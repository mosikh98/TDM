// ESLint flat config for the dashboard's plain browser scripts (web/static/*.js).
// The app itself is Python; this exists only to lint/format the front-end with
// https://github.com/SabziDev/eslint-rules  ->  pnpm install && pnpm lint:fix
import sabzidev from "@sabzidev/eslint-rules";
import { defineConfig } from "eslint/config";

export default defineConfig([
  {
    files: ["web/static/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      // These files are classic <script> tags (no import/export).
      sourceType: "script",
    },
    plugins: {
      "@sabzidev": sabzidev,
    },
    rules: {
      // Applied to the code base already (see the commit message).
      "@sabzidev/no-useless-template-literal": "warn",
      "@sabzidev/padding-before-jump-statement": "warn",

      // Not enabled on purpose:
      //  - merge-duplicate-id-and-classname-props, no-invalid-id-and-classname-value,
      //    sort-jsx-props   -> JSX only (there is no JSX here)
      //  - no-useless-empty-type -> TypeScript only
      //  - merge-exports         -> ES modules only (these are classic scripts)
      //  - sort-props, sort-comments -> reorder code/comments; review the diff before
      //    turning them on, since object/argument order can matter at runtime.
    },
  },
]);
