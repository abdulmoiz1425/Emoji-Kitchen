// This site does not use a service worker. This file exists only so that any
// service worker registered by an earlier version of the site (or during local
// testing) can fetch a valid response and immediately unregister itself,
// instead of repeatedly failing with a 404 on every page load.
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', async () => {
  await self.registration.unregister();
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach(client => client.navigate(client.url));
});
