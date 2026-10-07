async function loadHealth() {
  try {
    const response = await fetch('/');
    const data = await response.json();

    document.getElementById('status-value').textContent = data.status;
    document.getElementById('app-value').textContent = data.application;
    document.getElementById('version-value').textContent = data.version;
    document.getElementById('details').textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    document.getElementById('status-value').textContent = 'Erro';
    document.getElementById('app-value').textContent = 'API indisponível';
    document.getElementById('version-value').textContent = '-';
    document.getElementById('details').textContent = String(error);
  }
}

document.getElementById('refresh-button')?.addEventListener('click', loadHealth);
loadHealth();
