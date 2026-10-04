/**
 * Event Sanitization & Formatting Utility for Citizen Dashboard
 */

export function isTestEvent(event) {
  if (!event) return false;
  const title = (event.title || '').toLowerCase();
  const sourceId = (event.source_id || '').toLowerCase();
  const desc = (event.description || '').toLowerCase();

  return (
    title.includes('(test_') ||
    title.includes('test_opensearch') ||
    sourceId.startsWith('test_') ||
    desc.includes('(test_')
  );
}

export function sanitizeTitle(title) {
  if (!title) return 'Weather Incident';
  // Strip (test_...) patterns
  let clean = title.replace(/\(test_[^)]*\)/gi, '').trim();

  // Clean raw OpenWeather API strings like "Clear: clear sky in Lucknow, India Current weather in Lucknow..."
  if (clean.includes('Current weather in') || clean.includes('India Current weather')) {
    const parts = clean.split('Current weather in')[0].trim();
    if (parts) {
      const condition = parts.split(':')[0].trim();
      return condition ? condition.toUpperCase() : 'WEATHER OBSERVATION';
    }
  }

  return clean || 'Weather Incident';
}

export function formatCitizenEvent(event) {
  if (!event) return {};

  const cleanTitle = sanitizeTitle(event.title);
  let cleanDesc = (event.description || '').replace(/\(test_[^)]*\)/gi, '').trim();
  let eventType = event.event_type || 'WEATHER INCIDENT';

  // Format raw OpenWeather description string cleanly for citizens
  if (cleanDesc.includes('Current weather in') && cleanDesc.includes('Temperature:')) {
    const tempMatch = cleanDesc.match(/Temperature:\s*([\d.]+°C)/);
    const humMatch = cleanDesc.match(/Humidity:\s*(\d+%)/);
    const windMatch = cleanDesc.match(/Wind:\s*([\d.]+\s*m\/s)/);

    const metrics = [];
    if (tempMatch) metrics.push(`Temp: ${tempMatch[1]}`);
    if (humMatch) metrics.push(`Humidity: ${humMatch[1]}`);
    if (windMatch) metrics.push(`Wind: ${windMatch[1]}`);

    const cond = cleanTitle !== 'Weather Incident' ? cleanTitle : 'Observed Weather';
    cleanDesc = `${cond} reported in ${event.city || 'location'}. ${metrics.join(' · ')}`;
  }

  if (eventType === 'other' || eventType === 'OTHER') {
    const titleLower = cleanTitle.toLowerCase();
    if (titleLower.includes('rain') || titleLower.includes('drizzle')) eventType = 'rainfall';
    else if (titleLower.includes('clear')) eventType = 'clear_sky';
    else if (titleLower.includes('thunder')) eventType = 'thunderstorm';
    else if (titleLower.includes('fog') || titleLower.includes('mist')) eventType = 'fog';
    else if (titleLower.includes('heat')) eventType = 'heatwave';
    else if (titleLower.includes('wind')) eventType = 'strong_winds';
  }

  return {
    ...event,
    title: cleanTitle,
    description: cleanDesc,
    event_type: eventType,
  };
}
