import assert from 'node:assert/strict'
import { test } from 'node:test'

import { en, fi } from '../../src/i18n/messages.ts'
import { format, localizedName } from '../../src/lib/names.ts'

function leaves(value: unknown, path = ''): Map<string, string> {
  const result = new Map<string, string>()
  if (typeof value === 'string') result.set(path, value)
  else if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      for (const [p, v] of leaves(child, path ? `${path}.${key}` : key)) result.set(p, v)
    }
  }
  return result
}

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

test('Finnish has every English text with the same placeholders', () => {
  const english = leaves(en)
  const finnish = leaves(fi)
  assert.deepEqual([...finnish.keys()].sort(), [...english.keys()].sort())
  for (const [key, text] of english) {
    assert.ok(finnish.get(key)?.trim(), `${key} is empty in Finnish`)
    assert.deepEqual(placeholders(finnish.get(key)!), placeholders(text), key)
  }
  assert.equal(fi.months.length, 12)
})

test('formatting and localized names', () => {
  assert.equal(format('Bed {n}', { n: 3 }), 'Bed 3')
  assert.equal(format('{missing}', {}), '{missing}')
  assert.equal(localizedName({ en: 'Garlic', fi: 'Valkosipuli' }, 'fi'), 'Valkosipuli')
  assert.equal(localizedName({ en: 'Garlic' }, 'fi'), 'Garlic')
})
