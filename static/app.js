let allGroups = [];
let allResources = [];
let currentUser = JSON.parse(localStorage.getItem('studyloop_user') || 'null');

document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  loadGroups();
  loadResources();
});

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3200);
}

function updateAuthUI() {
  const authArea = document.getElementById('auth-area');
  if (currentUser) {
    authArea.innerHTML = `
      <div class="user-chip">
        <span>${escapeHtml(currentUser.name)} (${escapeHtml(currentUser.branch || 'IIITL')})</span>
        <button class="btn btn-secondary btn-sm" onclick="logoutUser()">Logout</button>
      </div>
    `;
  } else {
    authArea.innerHTML = `
      <button class="btn btn-primary" onclick="scrollToLogin()">Sign In with @iiitl.ac.in</button>
    `;
  }
}

function scrollToLogin() {
  document.getElementById('quick-email').focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function logoutUser() {
  localStorage.removeItem('studyloop_user');
  currentUser = null;
  updateAuthUI();
  showToast('Signed out from StudyLoop');
}

async function handleQuickLogin(event) {
  event.preventDefault();
  const name = document.getElementById('quick-name').value.trim();
  const email = document.getElementById('quick-email').value.trim();
  const branch = document.getElementById('quick-branch').value;
  const batch_year = parseInt(document.getElementById('quick-batch').value, 10);
  const msgEl = document.getElementById('quick-auth-msg');

  msgEl.textContent = 'Verifying IIITL credentials...';
  msgEl.className = 'form-feedback';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, branch, batch_year, campus_id: 'iiitl' })
    });
    const data = await res.json();

    if (!res.ok) {
      msgEl.textContent = data.error || 'Verification failed.';
      msgEl.className = 'form-feedback feedback-error';
      return;
    }

    currentUser = data.user;
    localStorage.setItem('studyloop_user', JSON.stringify(currentUser));
    updateAuthUI();
    msgEl.textContent = `Welcome, ${currentUser.name}! Campus access unlocked.`;
    msgEl.className = 'form-feedback feedback-success';
    showToast(`Signed in as ${currentUser.name}`);
  } catch (err) {
    msgEl.textContent = 'Network error. Please try again.';
    msgEl.className = 'form-feedback feedback-error';
  }
}

async function loadGroups() {
  try {
    const res = await fetch('/api/groups?campus_id=iiitl');
    allGroups = await res.json();
    document.getElementById('stat-groups').textContent = allGroups.length;
    renderGroups(allGroups);
  } catch (err) {
    console.error('Failed to load groups:', err);
  }
}

function filterGroups() {
  const query = document.getElementById('group-search').value.toLowerCase().trim();
  const branch = document.getElementById('branch-filter').value;

  const filtered = allGroups.filter(g => {
    const matchesText =
      g.title.toLowerCase().includes(query) ||
      g.subject_code.toLowerCase().includes(query) ||
      (g.description || '').toLowerCase().includes(query);
    const matchesBranch =
      branch === 'ALL' ||
      (g.branch || '').toUpperCase().includes(branch) ||
      (g.branch || '').toUpperCase() === 'ALL';
    return matchesText && matchesBranch;
  });

  renderGroups(filtered);
}

function renderGroups(groups) {
  const grid = document.getElementById('groups-grid');
  if (!groups.length) {
    grid.innerHTML = `<p class="muted-text">No study groups match your filter yet. Start the first one!</p>`;
    return;
  }

  grid.innerHTML = groups.map(g => `
    <article class="group-card">
      <div>
        <div class="card-badges">
          <span class="code-badge">${escapeHtml(g.subject_code)}</span>
          <span class="branch-tag">${escapeHtml(g.branch || 'All Branches')}</span>
        </div>
        <h3>${escapeHtml(g.title)}</h3>
        <p class="group-desc">${escapeHtml(g.description || 'Peer study group for IIIT Lucknow students.')}</p>
      </div>
      <div>
        <div class="group-meta">
          <span><strong>When:</strong> ${escapeHtml(g.schedule || 'Flexible')}</span>
          <span><strong>Where:</strong> ${escapeHtml(g.location || 'Campus / Online')}</span>
          <span><strong>Host:</strong> ${escapeHtml(g.created_by || 'IIITL Peer')}</span>
        </div>
        <div class="group-footer">
          <span class="member-pill" id="members-${g.id}">${g.members_count || 1} Peers Joined</span>
          <button class="btn btn-primary btn-sm" onclick="joinGroup(${g.id})">Join Circle</button>
        </div>
      </div>
    </article>
  `).join('');
}

async function joinGroup(groupId) {
  try {
    const res = await fetch(`/api/groups/${groupId}/join`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      const target = allGroups.find(g => g.id === groupId);
      if (target) target.members_count = data.members_count;
      const pill = document.getElementById(`members-${groupId}`);
      if (pill) pill.textContent = `${data.members_count} Peers Joined`;
      showToast('You joined the study circle!');
    }
  } catch (err) {
    showToast('Could not join right now.');
  }
}

async function loadResources() {
  try {
    const res = await fetch('/api/resources?campus_id=iiitl');
    allResources = await res.json();
    document.getElementById('stat-resources').textContent = allResources.length;
    renderResources(allResources);
  } catch (err) {
    console.error('Failed to load resources:', err);
  }
}

function renderResources(resources) {
  const grid = document.getElementById('resources-grid');
  if (!resources.length) {
    grid.innerHTML = `<p class="muted-text">No notes or PYQs uploaded yet.</p>`;
    return;
  }

  grid.innerHTML = resources.map(r => `
    <div class="resource-card">
      <div>
        <div class="card-badges">
          <span class="code-badge">${escapeHtml(r.subject_code)}</span>
          <span class="res-type-badge">${escapeHtml(r.resource_type)}</span>
        </div>
        <h4>${escapeHtml(r.title)}</h4>
      </div>
      <div class="resource-footer">
        <span>By ${escapeHtml(r.shared_by || 'IIITL Student')}</span>
        <a href="${escapeAttr(r.link)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm">Open &nearr;</a>
      </div>
    </div>
  `).join('');
}

function openGroupModal() {
  document.getElementById('group-modal').classList.remove('hidden');
}

function openResourceModal() {
  document.getElementById('resource-modal').classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

async function handleCreateGroup(event) {
  event.preventDefault();
  const payload = {
    title: document.getElementById('group-title').value.trim(),
    subject_code: document.getElementById('group-code').value.trim(),
    branch: document.getElementById('group-branch').value,
    schedule: document.getElementById('group-schedule').value.trim(),
    location: document.getElementById('group-location').value.trim(),
    description: document.getElementById('group-desc').value.trim(),
    created_by: currentUser ? `${currentUser.name} (${currentUser.branch || 'IIITL'})` : 'IIITL Student',
    campus_id: 'iiitl'
  };

  const res = await fetch('/api/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    closeModal('group-modal');
    event.target.reset();
    await loadGroups();
    showToast('Study group published!');
  }
}

async function handleCreateResource(event) {
  event.preventDefault();
  const payload = {
    title: document.getElementById('res-title').value.trim(),
    subject_code: document.getElementById('res-code').value.trim(),
    resource_type: document.getElementById('res-type').value,
    link: document.getElementById('res-link').value.trim(),
    shared_by: currentUser ? currentUser.name : 'IIITL Student',
    campus_id: 'iiitl'
  };

  const res = await fetch('/api/resources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    closeModal('resource-modal');
    event.target.reset();
    await loadResources();
    showToast('Resource added to campus vault!');
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeAttr(url) {
  const clean = String(url).trim();
  if (/^https?:\/\//i.test(clean)) return clean;
  return '#';
}
