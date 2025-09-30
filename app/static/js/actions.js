import { dom } from './dom.js';
import { state } from './state.js';

export const setLoading = (loading, message = 'Ready') => {
    state.isLoading = loading;
    dom.spinner.classList.toggle('hidden', !loading);
    dom.userInput.disabled = loading;
    dom.sendBtn.disabled = loading;
    dom.aiStatusText.textContent = message;
};

export const showToast = (message, type = 'success') => {
    dom.toast.textContent = message;
    dom.toast.className = type;
    dom.toast.classList.add('show');
    setTimeout(() => dom.toast.classList.remove('show'), 3000);
};

export const autoResizeTextarea = () => {
    dom.userInput.style.height = 'auto';
    dom.userInput.style.height = `${Math.min(dom.userInput.scrollHeight, 200)}px`;
};

export const renderProjects = () => {
    dom.projectList.innerHTML = '';
    if (state.projects.length === 0) {
        dom.projectList.innerHTML = '<div class="empty-state">No projects yet</div>';
    } else {
        state.projects.forEach(p => {
            const div = document.createElement('div');
            div.className = `list-item ${p.id === state.currentProjectId ? 'active' : ''}`;
            div.dataset.projectId = p.id;
            div.innerHTML = `
                <span class="list-item-text">${p.name}</span>
                <button class="btn-icon delete-btn" data-project-id="${p.id}" title="Delete project">
                    <i class="fas fa-trash-alt"></i>
                </button>
            `;
            dom.projectList.appendChild(div);
        });
    }
};

export const renderConversations = () => {
    dom.convList.innerHTML = '';
    dom.newConvBtn.disabled = !state.currentProjectId;
    
    if (!state.currentProjectId) {
        dom.convList.innerHTML = '<div class="empty-state">Select a project first</div>';
    } else if (state.conversations.length === 0) {
        dom.convList.innerHTML = '<div class="empty-state">No conversations yet</div>';
    } else {
        state.conversations.forEach(c => {
            const div = document.createElement('div');
            div.className = `list-item ${c.id === state.currentConvId ? 'active' : ''}`;
            div.dataset.convId = c.id;
            div.innerHTML = `
                <span class="list-item-text">${c.title}</span>
                <button class="btn-icon delete-btn" data-conv-id="${c.id}" title="Delete conversation">
                    <i class="fas fa-trash-alt"></i>
                </button>
            `;
            dom.convList.appendChild(div);
        });
    }
};

export const renderAttachments = (files) => {
    dom.fileList.innerHTML = '';
    dom.uploadFileBtn.disabled = !state.currentConvId;
    
    if (!state.currentConvId) {
        dom.fileList.innerHTML = '<div class="empty-state">Select a conversation</div>';
    } else if (files.length === 0) {
        dom.fileList.innerHTML = '<div class="empty-state">No files attached<br><small>Click upload to add files</small></div>';
    } else {
        files.forEach(f => {
            const div = document.createElement('div');
            div.className = 'attachment-item';
            
            const statusIcons = {
                'original': '📄',
                'modified': '✏️',
                'latest': '✨'
            };
            const statusIcon = statusIcons[f.status] || '📄';
            const sizeKB = (f.size_bytes / 1024).toFixed(1);
            
            div.innerHTML = `
                <div class="attachment-header">
                    <span class="attachment-icon">${statusIcon}</span>
                    <span class="attachment-name" title="${f.filename}">${f.filename}</span>
                    <span class="attachment-version">v${f.version}</span>
                </div>
                <div class="attachment-meta">
                    <span class="attachment-size">${sizeKB} KB</span>
                    ${f.modification_summary ? `<span class="attachment-summary">${f.modification_summary}</span>` : ''}
                </div>
                <div class="attachment-actions">
                    <button class="btn-icon-small" onclick="actions.handleDownloadAttachment(${f.id}, '${f.filename}')" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn-icon-small" onclick="actions.handleViewVersions(${f.id})" title="Version history">
                        <i class="fas fa-history"></i>
                    </button>
                    <button class="btn-icon-small delete-btn" onclick="actions.handleDeleteAttachment(${f.id})" title="Delete file">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
            dom.fileList.appendChild(div);
        });
    }
};

export const processCodeBlocks = (element) => {
    element.querySelectorAll('pre code').forEach(block => {
        if (block.dataset.highlighted) return;
        hljs.highlightElement(block);
        block.dataset.highlighted = 'true';
        
        const pre = block.parentElement;
        if (pre.parentElement.classList.contains('code-block-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
        
        const toolbar = document.createElement('div');
        toolbar.className = 'code-toolbar';
        
        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => copyBtn.textContent = 'Copy', 2000);
            });
        };
        toolbar.appendChild(copyBtn);
        wrapper.appendChild(toolbar);
    });
};

export const appendMessage = (role, content) => {
    dom.welcomeMessage.classList.add('hidden');
    dom.chatMessages.classList.remove('hidden');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = marked.parse(content);
    dom.chatMessages.appendChild(div);
    processCodeBlocks(div);
    return div;
};

export const renderChats = (chats) => {
    dom.welcomeMessage.classList.add('hidden');
    dom.chatMessages.classList.remove('hidden');
    dom.chatMessages.innerHTML = '';
    chats.forEach(chat => {
        appendMessage('user', chat.message);
        appendMessage('ai', chat.ai_response);
    });
    dom.chatWindow.scrollTop = dom.chatWindow.scrollHeight;
};

export const closeSidebars = () => {
    dom.sidebarLeft.classList.remove('open');
    dom.sidebarRight.classList.remove('open');
    dom.mobileOverlay.classList.add('hidden');
};
