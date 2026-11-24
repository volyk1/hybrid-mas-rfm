const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const btnSubmit = document.getElementById('btn-submit');
const btnNewChat = document.getElementById('btn-new-chat');
const sessionsContainer = document.getElementById('sessions-container');
const lblHistory = document.getElementById('lbl-history');
const lblHeaderTitle = document.getElementById('lbl-header-title');
const btnUa = document.getElementById('btn-ua');
const btnEn = document.getElementById('btn-en');

// Контекстне меню та модалка
const contextMenu = document.getElementById('session-context-menu');
const menuBtnRename = document.getElementById('menu-btn-rename');
const menuBtnDelete = document.getElementById('menu-btn-delete');
const lblMenuRename = document.getElementById('lbl-menu-rename');
const lblMenuDelete = document.getElementById('lbl-menu-delete');

const renameModal = document.getElementById('rename-modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalRenameInput = document.getElementById('modal-rename-input');
const modalBtnCancel = document.getElementById('modal-btn-cancel');
const modalBtnConfirm = document.getElementById('modal-btn-confirm');

let currentSessionId = null;
let targetSessionForMenu = null; // ID сесії, для якої відкрито меню
let isGenerating = false;
let abortController = null;
let currentLang = localStorage.getItem('mas_lang') || 'ua';

const DICTIONARY = {
    ua: {
        newChat: '+ Новий чат',
        history: 'АРХІВ ОБГОВОРЕНЬ',
        title: 'МУЛЬТИАГЕНТНА АНАЛІТИЧНА СИСТЕМА',
        placeholder: 'Введіть аналітичний запит...',
        statusInit: '🧬 Синхронізація семантичного простору агентури...',
        stopMsg: '🛑 Генерацію примусово перервано користувачем.',
        errorConn: 'Помилка з\'єднання із сервером.',
        delConfirm: 'Видалити цю сесію з терміналу?',
        menuRename: 'Перейменувати',
        menuDelete: 'Видалити',
        modalTitle: 'Перейменуйте цей чат',
        btnCancel: 'Скасувати',
        btnRename: 'Перейменувати',
        welcome: `
            <h3>🏛️ Інтелектуальна СППР на базі MAS-архітектури</h3>
            <p>
                <strong>Цільове призначення:</strong> Автоматизація процесів підтримки прийняття управлінських рішень в e-commerce на основі інтелектуальної сегментації клієнтської бази.<br><br>
                <strong>Контур взаємодії (MAS):</strong><br>
                • 🕵️ <em>Агент-Аналітик:</em> парсинг транзакційних метрик Qdrant та моніторинг зовнішнього ринкового контексту.<br>
                • 🛡️ <em>Агент-Критик:</em> крос-валідація гіпотез, аудит логічних розбіжностей та оцінка ризиків.<br>
                • 👑 <em>Агент-Менеджер:</em> агрегація експертних оцінок, пошук консенсусу та формування фінальної керуючої матриці.
            </p>`
    },
    en: {
        newChat: '+ New Chat',
        history: 'DISCUSSION ARCHIVE',
        title: 'MULTI-AGENT ANALYTICAL SYSTEM',
        placeholder: 'Enter analytical query...',
        statusInit: '🧬 Synchronizing agent semantic space...',
        stopMsg: '🛑 Generation forcibly interrupted by user.',
        errorConn: 'Server connection error.',
        delConfirm: 'Delete this session from terminal?',
        menuRename: 'Rename',
        menuDelete: 'Delete',
        modalTitle: 'Rename this chat',
        btnCancel: 'Cancel',
        btnRename: 'Rename',
        welcome: `
            <h3>🏛️ Intelligent DSS based on MAS Architecture</h3>
            <p>
                <strong>Target Purpose:</strong> Automation of managerial decision-making support in e-commerce based on intelligent customer base segmentation.<br><br>
                <strong>Interaction Contour (MAS):</strong><br>
                • 🕵️ <em>Analyst Agent:</em> parsing Qdrant transactional metrics and monitoring external market context.<br>
                • 🛡️ <em>Critic Agent:</em> cross-validation of hypotheses, audit of logical discrepancies, and risk assessment.<br>
                • 👑 <em>Manager Agent:</em> aggregation of expert assessments, consensus seeking, and control matrix generation.
            </p>`
    }
};

function applyLanguageUI() {
    const dict = DICTIONARY[currentLang];
    btnNewChat.textContent = dict.newChat;
    lblHistory.textContent = dict.history;
    lblHeaderTitle.textContent = dict.title;
    userInput.placeholder = dict.placeholder;

    lblMenuRename.textContent = dict.menuRename;
    lblMenuDelete.textContent = dict.menuDelete;
    modalTitle.textContent = dict.modalTitle;
    modalBtnCancel.textContent = dict.btnCancel;
    modalBtnConfirm.textContent = dict.btnRename;

    if (currentLang === 'en') {
        btnEn.classList.add('active');
        btnUa.classList.remove('active');
    } else {
        btnUa.classList.add('active');
        btnEn.classList.remove('active');
    }

    const welcomeMsg = document.getElementById('welcome-msg');
    if (welcomeMsg) {
        welcomeMsg.innerHTML = dict.welcome;
    }
}

function switchLanguage(lang) {
    if (currentLang === lang) return;
    currentLang = lang;
    localStorage.setItem('mas_lang', lang);
    applyLanguageUI();
}

async function loadSessions() {
    try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        sessionsContainer.innerHTML = '';
        
        data.forEach(s => {
            const div = document.createElement('div');
            div.className = `session-item ${s.id === currentSessionId ? 'active' : ''}`;
            div.onclick = () => { if (!isGenerating) switchSession(s.id); };
            
            const titleSpan = document.createElement('span');
            titleSpan.className = 'session-title';
            titleSpan.textContent = s.title;
            div.appendChild(titleSpan);

            // Кнопка три крапки (⋮)
            const moreBtn = document.createElement('button');
            moreBtn.className = 'btn-more';
            moreBtn.innerHTML = '⋮';
            moreBtn.onclick = (e) => {
                e.stopPropagation();
                if (!isGenerating) openContextMenu(e, s);
            };
            div.appendChild(moreBtn);

            sessionsContainer.appendChild(div);
        });
    } catch (err) { console.error("Помилка завантаження сесій:", err); }
}

/* КОНТЕКСТНЕ МЕНЮ */
function openContextMenu(e, session) {
    closeContextMenu();
    targetSessionForMenu = session;

    const rect = e.target.getBoundingClientRect();
    contextMenu.style.top = `${rect.bottom + 4}px`;
    contextMenu.style.left = `${rect.left - 130}px`;
    contextMenu.classList.remove('hidden');

    e.target.classList.add('active-menu');
}

function closeContextMenu() {
    contextMenu.classList.add('hidden');
    document.querySelectorAll('.btn-more').forEach(b => b.classList.remove('active-menu'));
}

/* ВІДКРИТТЯ МОДАЛКИ ПЕРЕЙМЕНУВАННЯ */
function openRenameModal() {
    if (!targetSessionForMenu) return;
    modalRenameInput.value = targetSessionForMenu.title;
    renameModal.classList.remove('hidden');
    document.body.classList.add('modal-open');
    modalRenameInput.focus();
    modalRenameInput.select();
}

function closeRenameModal() {
    renameModal.classList.add('hidden');
    document.body.classList.remove('modal-open');
}

async function submitRename() {
    const newTitle = modalRenameInput.value.trim();
    if (!newTitle || !targetSessionForMenu) return;

    try {
        const res = await fetch(`/api/sessions/${targetSessionForMenu.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        if (res.ok) {
            closeRenameModal();
            loadSessions();
        }
    } catch (err) {
        console.error("Помилка перейменування:", err);
    }
}

// Події кнопок меню
menuBtnRename.onclick = () => {
    closeContextMenu();
    openRenameModal();
};

menuBtnDelete.onclick = () => {
    closeContextMenu();
    if (targetSessionForMenu) {
        deleteSession(targetSessionForMenu.id);
    }
};

modalBtnCancel.onclick = closeRenameModal;
modalBtnConfirm.onclick = submitRename;

modalRenameInput.onkeydown = (e) => {
    if (e.key === 'Enter') submitRename();
    if (e.key === 'Escape') closeRenameModal();
};

// Закриття меню при кліку зовні
document.addEventListener('click', (e) => {
    if (!contextMenu.contains(e.target)) {
        closeContextMenu();
    }
});

sessionsContainer.addEventListener('scroll', closeContextMenu);

async function switchSession(id) {
    currentSessionId = id;
    document.getElementById('welcome-msg')?.remove();
    chatBox.innerHTML = '';
    loadSessions();
    try {
        const res = await fetch(`/api/sessions/${id}`);
        const history = await res.json();
        history.forEach(msg => {
            appendMessage(msg.role === 'user' ? 'user' : 'assistant', msg.text);
        });
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (err) { console.error("Помилка завантаження історії:", err); }
}

async function deleteSession(id) {
    if (!confirm(DICTIONARY[currentLang].delConfirm)) return;
    await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
    if (currentSessionId === id) {
        currentSessionId = null;
        chatBox.innerHTML = `<div class="welcome-banner" id="welcome-msg">${DICTIONARY[currentLang].welcome}</div>`;
    }
    loadSessions();
}

function appendMessage(role, text) {
    document.getElementById('welcome-msg')?.remove();
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.textContent = text;

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(content);
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function handleAction() {
    if (isGenerating) {
        stopGeneration();
    } else {
        sendRequest();
    }
}

function stopGeneration() {
    if (abortController) {
        abortController.abort();
    }
    document.getElementById('live-status-block')?.remove();
    appendMessage('assistant', DICTIONARY[currentLang].stopMsg);
    resetInputState();
}

function resetInputState() {
    isGenerating = false;
    userInput.disabled = false;
    btnSubmit.className = 'btn-send';
    btnSubmit.textContent = '➔';
    userInput.focus();
    loadSessions();
}

async function sendRequest() {
    const query = userInput.value.trim();
    if (!query) return;

    appendMessage('user', query);
    userInput.value = '';
    
    isGenerating = true;
    userInput.disabled = true;
    btnSubmit.className = 'btn-send stop-mode';
    btnSubmit.textContent = '■';

    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-container';
    statusDiv.id = 'live-status-block';
    
    const textSpan = document.createElement('span');
    textSpan.className = 'status-text';
    textSpan.id = 'status-dynamic-text';
    textSpan.textContent = DICTIONARY[currentLang].statusInit;
    
    const lineContainer = document.createElement('div');
    lineContainer.className = 'progress-line-container';
    const lineActive = document.createElement('div');
    lineActive.className = 'progress-line-active';
    
    lineContainer.appendChild(lineActive);
    statusDiv.appendChild(textSpan);
    statusDiv.appendChild(lineContainer);
    chatBox.appendChild(statusDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    abortController = new AbortController();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: query, 
                session_id: currentSessionId,
                lang: currentLang 
            }),
            signal: abortController.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.type === 'session') {
                            if (!currentSessionId) {
                                currentSessionId = data.id;
                            }
                        } else if (data.type === 'status') {
                            const el = document.getElementById('status-dynamic-text');
                            if (el) el.textContent = data.text;
                        } else if (data.type === 'final') {
                            document.getElementById('live-status-block')?.remove();
                            appendMessage('assistant', data.text);
                        }
                    } catch (e) {}
                }
            });
        }
    } catch (err) {
        if (err.name === 'AbortError') return;
        document.getElementById('live-status-block')?.remove();
        appendMessage('assistant', DICTIONARY[currentLang].errorConn);
    } finally {
        resetInputState();
    }
}

btnSubmit.onclick = handleAction;
userInput.onkeydown = (e) => { if (e.key === 'Enter' && !isGenerating) sendRequest(); };

btnNewChat.onclick = () => {
    if (isGenerating) return;
    currentSessionId = null;
    chatBox.innerHTML = `<div class="welcome-banner" id="welcome-msg">${DICTIONARY[currentLang].welcome}</div>`;
    loadSessions();
    userInput.focus();
};

applyLanguageUI();
loadSessions();