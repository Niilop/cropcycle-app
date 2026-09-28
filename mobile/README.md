# CropCycle mobile app

Expo (SDK 57) app for iOS, Android and the web, using Expo Router, TanStack Query and Zustand. Planning logic and crop rules live in the backend; this app only displays and edits data.

## Running it

Start the API first, from the repository root (`make dev` or `make backend`), with the database migrated and seeded. Then, in a second terminal:

```bash
make mobile          # or: cd mobile && npx expo start
```

Expo prints a QR code and a menu. From there you can use any of three views.

### 1. Browser (quickest)

Press **w**, or open <http://localhost:8081> in Chrome or Edge on Windows.

- **Phone or tablet sizes:** press **F12**, then **Ctrl+Shift+M** for the device toolbar.
  - Pick a device such as iPad Air or Pixel Tablet (tablet-first layout), or iPhone 14 or Pixel 7.
  - The rotate button switches between landscape and portrait.
- **CORS:** the API must allow the web origin. Your repository-root `.env` needs `CORS_ORIGINS=http://localhost:8081` (the default in `.env.example`); restart the API after changing it.
- **Sign-in:** on the web the token is kept in the browser's `localStorage`. Native apps use the device keychain (`expo-secure-store`).

### 2. Android emulator on Windows

1. Install Android Studio on Windows. In **Device Manager**, create a _Pixel Tablet_ and/or a _Pixel 7_ with a Play Store system image.
2. Start the emulator and install **Expo Go** from the Play Store.
3. In Expo Go, choose **Enter URL manually**: `exp://10.0.2.2:8081`.

The app then finds the API at `http://10.0.2.2:8000` automatically.

### 3. Your phone or tablet (Expo Go)

1. Install **Expo Go** from the App Store or Play Store.
2. Your phone must reach WSL. Create `C:\Users\<you>\.wslconfig` with:

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

   Notepad may save this as `.wslconfig.txt`, which WSL ignores. In File Explorer, turn on **View → Show → File name extensions** to check the name.

3. Run `wsl --shutdown` in PowerShell, and allow ports 8081 and 8000 when Windows Firewall asks. After the restart, `make mobile` should show `Metro: exp://<your PC's Wi-Fi address>:8081`, not a `172.x` address.
4. Start the API so the network can reach it: `make dev BACKEND_HOST=0.0.0.0` (or `make backend BACKEND_HOST=0.0.0.0` for the API alone). Without `BACKEND_HOST=0.0.0.0`, the API only listens on this computer and the app shows "cannot reach server". To check, open `http://<your PC's Wi-Fi address>:8000/docs` in the phone's browser.
5. Scan the QR code with the Camera app (iPhone) or with Expo Go (Android).

The iOS Simulator needs a Mac; on Windows, use Expo Go on an iPhone or iPad. Standalone builds come later through EAS (plan 002, Phase 5).

### API address

The app calls port 8000 on the host that served it: `localhost` in a browser, `10.0.2.2` in the emulator, or your PC's address in Expo Go. To use another API, set `EXPO_PUBLIC_API_URL` in `mobile/.env.local` (see `.env.example`) and restart with `npx expo start --clear`. The value is built into the bundle, and without `--clear` a cached bundle keeps the old address. **Settings → Server** shows the address in use.

## Checks

```bash
make check-mobile    # all of the below
npm run lint         # ESLint (expo lint, React Compiler rules)
npm run format:check # Prettier
npm run typecheck    # TypeScript
npm run test:unit    # Node's test runner: months, geometry, translations
npm run api:check    # generated API types match the backend
npm run test:e2e     # Playwright: tablet and phone views against a fake API
```

`test:e2e` exports the web build with `EXPO_PUBLIC_API_URL=http://api.test`, serves it with `e2e/serve.mjs`, and intercepts that host with `e2e/fake-api.ts`. No backend or database is needed. Chromium comes from `npx playwright install chromium`.

## API types

`src/api/schema.d.ts` and `src/api/openapi.json` are generated from the FastAPI app (D010). After changing backend routes or schemas, run `npm run api:types` and commit both files. A backend test and `api:check` fail when they are stale.

## Structure

```text
src/app/          Routes (Expo Router): sign-in, register, gardens, (tabs)/ garden · plan · history · settings
src/api/          Fetch client, API address, generated types, TanStack Query hooks
src/auth/         Session store (token + user, persisted) and the sign-in/register form
src/garden/       Garden canvas (tap, drag, resize), bed panel, planting form, season timeline
src/state/        Preferences (language, active garden) and transient editor state
src/i18n/         English and Finnish texts; crop names come from the catalogue
src/lib/          Pure helpers (months, geometry, names, storage), unit-tested with Node
src/ui/           Theme and shared components (buttons, fields, steppers, chips, screen)
e2e/              Playwright tests, fake API and the static server
```

Every edit can be done by tapping: select a bed, then use the panel's fields and ± buttons. Dragging beds in **Edit layout** is a shortcut (D011). Text must exist in both `en` and `fi` in `src/i18n/messages.ts`; a unit test checks this.
