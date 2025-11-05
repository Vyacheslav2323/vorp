
export function getBase() {
  const protocol = location.protocol;
  const hostname = location.hostname;
  const port = location.port;
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    if (port === '8000') {
      return '';
    }
    return `${protocol}//${hostname}:8000`;
  }
  
  if (port && port !== '80' && port !== '443') {
    return `${protocol}//${hostname}:${port}`;
  }
  
  return '';
}

export function parseCSV(x) {
  const rows = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < x.length; i++) {
    if (x[i] === '"') inQuotes = !inQuotes;
    else if (x[i] === ',' && !inQuotes) {
      rows.push(current);
      current = '';
    } else if ((x[i] === '\n' || x[i] === '\r') && !inQuotes) {
      if (current) rows.push(current);
      return rows;
    } else {
      current += x[i];
    }
  }
  if (current) rows.push(current);
  return rows;
}

export async function speakText(text, lang = 'ko') {
  const response = await fetch(`${getBase()}/tts`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text, lang})
  });
  const result = await response.json();
  if (result.success && result.audio) {
    const audio = new Audio(`data:audio/mp3;base64,${result.audio}`);
    audio.play();
    return true;
  }
  return false;
}

