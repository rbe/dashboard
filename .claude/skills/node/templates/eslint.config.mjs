// ESLint is the one linter. This is the flat config for a Node project
// that uses ES modules. Add rules here. Do not add a second linter.
import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: [".claude/", "apm_modules/", "build/", "coverage/", "dist/"] },
  js.configs.recommended,
  { languageOptions: { globals: { ...globals.node } } },
];
