import fs from 'fs';
import { execSync } from 'child_process';

if (!fs.existsSync('.env')) {
  console.error('❌ .env file not found!');
  process.exit(1);
}

const envContent = fs.readFileSync('.env', 'utf-8');
const lines = envContent.split(/\r?\n/);

const secretKeys = ['PROXY_HOST', 'PROXY_PORT', 'PROXY_AUTH', 'TARGET_UPSTREAM_URL', 'NGROK_URL', 'NGROK_AUTHTOKEN'];

console.log('==================================================');
console.log('🚀 Syncing secrets from .env to Cloudflare Workers...');
console.log('==================================================');

for (const line of lines) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) continue;
  const idx = trimmed.indexOf('=');
  if (idx === -1) continue;
  const key = trimmed.slice(0, idx).trim();
  const val = trimmed.slice(idx + 1).trim();

  if (secretKeys.includes(key) && val) {
    try {
      console.log(`Setting Cloudflare secret: ${key}...`);
      execSync(`npx wrangler secret put ${key}`, {
        input: val,
        stdio: ['pipe', 'inherit', 'inherit'],
        encoding: 'utf-8'
      });
      console.log(`✓ ${key} set successfully.\n`);
    } catch (e) {
      console.error(`Failed to set ${key}: ${e.message}`);
    }
  }
}

console.log('🎉 Done! All secrets are now securely saved in Cloudflare Workers.');
