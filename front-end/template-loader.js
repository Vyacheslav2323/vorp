export async function loadTemplate(templateName) {
  const response = await fetch(`templates/${templateName}.html`);
  if (!response.ok) {
    throw new Error(`Failed to load template: ${templateName} (${response.status})`);
  }
  return await response.text();
}

export async function loadTemplateIntoContainer(containerId, templateName) {
  const container = document.getElementById(containerId);
  if (!container) {
    throw new Error(`Container not found: ${containerId}`);
  }
  const templateContent = await loadTemplate(templateName);
  container.innerHTML = templateContent;
}
