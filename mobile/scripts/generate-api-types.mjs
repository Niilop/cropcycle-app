// Generates src/api/openapi.json and src/api/schema.d.ts from the FastAPI app (D010).
// `--check` fails if the committed files are stale. Needs uv (repository root) and npx.
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// openapi-typescript 7 declares a TypeScript 5 peer; this app uses TypeScript 6, so the
// generator runs in its own pinned npx environment instead of being a project dependency.
const GENERATOR = [
  '-p',
  'typescript@5.9.3',
  '-p',
  'openapi-typescript@7.13.0',
  'openapi-typescript',
]

const mobile = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(mobile, '..')
const check = process.argv.includes('--check')
const target = join(mobile, 'src', 'api')
const out = check ? mkdtempSync(join(tmpdir(), 'cropcycle-api-')) : target

try {
  const schema = execFileSync(
    'uv',
    ['run', '--no-sync', 'python', '-m', 'scripts.export_openapi'],
    {
      cwd: root,
      encoding: 'utf8',
    },
  )
  writeFileSync(join(out, 'openapi.json'), schema)
  execFileSync(
    'npx',
    ['--yes', ...GENERATOR, join(out, 'openapi.json'), '--output', join(out, 'schema.d.ts')],
    { cwd: mobile, stdio: ['ignore', 'ignore', 'inherit'] },
  )
  if (check) {
    const stale = ['openapi.json', 'schema.d.ts'].filter(
      (name) => readFileSync(join(out, name), 'utf8') !== readFileSync(join(target, name), 'utf8'),
    )
    if (stale.length) {
      console.error(`Stale API types: ${stale.join(', ')}. Run \`npm run api:types\`.`)
      process.exitCode = 1
    } else {
      console.log('API types are up to date.')
    }
  } else {
    console.log('Generated src/api/openapi.json and src/api/schema.d.ts.')
  }
} finally {
  if (check) rmSync(out, { recursive: true, force: true })
}
