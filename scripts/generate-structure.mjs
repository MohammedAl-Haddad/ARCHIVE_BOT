import { promises as fs } from 'fs';
import path from 'path';

const ROOT = process.cwd();
const MAX_FILE_SIZE = 1024 * 1024; // 1MB
const IGNORED = new Set(['node_modules', '.git', 'dist', 'build', '.turbo', 'coverage', '.cache', '.next', 'out', 'tmp', '.vscode', '.idea']);

const languageMap = {
  '.js': 'JavaScript',
  '.mjs': 'JavaScript',
  '.ts': 'TypeScript',
  '.py': 'Python',
  '.json': 'JSON',
  '.md': 'Markdown',
  '.yml': 'YAML',
  '.yaml': 'YAML',
  '.html': 'HTML',
  '.css': 'CSS',
  '.txt': 'Text'
};

const specialFiles = {
  'package.json': 'Project configuration and dependencies.',
  'README.md': 'Project overview and instructions.'
};

const dirDescriptions = {
  src: 'Source code.',
  scripts: 'Utility scripts.',
  tests: 'Test suite.',
  docs: 'Documentation.',
  '.github': 'GitHub configuration.',
  database: 'Database files.'
};

function specialDescription(name, relPath) {
  if (specialFiles[name]) return specialFiles[name];
  if (name.startsWith('tsconfig')) return 'TypeScript compiler configuration.';
  if (name.startsWith('vite.config')) return 'Vite build configuration.';
  if (name.startsWith('.eslintrc') || name === 'eslint.config.js') return 'ESLint configuration.';
  if (name.startsWith('.prettierrc') || name === 'prettier.config.js') return 'Prettier configuration.';
  if (relPath.includes('.github/workflows') && (name.endsWith('.yml') || name.endsWith('.yaml'))) return 'GitHub Actions workflow definition.';
  return null;
}

function defaultDescription(ext) {
  switch (ext) {
    case '.js':
    case '.mjs':
      return 'JavaScript source file.';
    case '.ts':
      return 'TypeScript source file.';
    case '.py':
      return 'Python source file.';
    case '.json':
      return 'JSON file.';
    case '.md':
      return 'Markdown document.';
    case '.yml':
    case '.yaml':
      return 'YAML configuration file.';
    case '.html':
      return 'HTML document.';
    case '.css':
      return 'CSS stylesheet.';
    case '.txt':
      return 'Text file.';
    default:
      return 'File.';
  }
}

function extractLeadingComment(content) {
  const lines = content.split(/\r?\n/);
  for (let i = 0; i < Math.min(lines.length, 20); i++) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.startsWith('#')) return line.replace(/^#\s*/, '').trim();
    if (line.startsWith('//')) return line.replace(/^\/\/\s*/, '').trim();
    if (line.startsWith('/*')) {
      let text = line.replace(/^\/\*\s*/, '');
      if (text.endsWith('*/')) return text.replace(/\*\/$/, '').trim();
      const parts = [];
      if (text) parts.push(text.trim());
      for (let j = i + 1; j < lines.length; j++) {
        const l = lines[j].trim();
        if (l.endsWith('*/')) {
          parts.push(l.replace(/\*\/$/, '').replace(/^\*\s*/, '').trim());
          return parts.join(' ');
        }
        parts.push(l.replace(/^\*\s*/, '').trim());
      }
    }
    if (line.startsWith('"""') || line.startsWith("''")) {
      const quote = line.slice(0, 3);
      let rest = line.slice(3);
      if (rest.includes(quote)) {
        return rest.slice(0, rest.indexOf(quote)).trim();
      }
      const parts = [];
      if (rest) parts.push(rest.trim());
      for (let j = i + 1; j < lines.length; j++) {
        const l = lines[j];
        if (l.includes(quote)) {
          parts.push(l.slice(0, l.indexOf(quote)).trim());
          return parts.join(' ').trim();
        }
        parts.push(l.trim());
      }
    }
    if (line.startsWith('<!--')) {
      let text = line.replace(/^<!--\s*/, '');
      if (text.endsWith('-->')) return text.replace(/-->$/, '').trim();
      const parts = [];
      if (text) parts.push(text.trim());
      for (let j = i + 1; j < lines.length; j++) {
        const l = lines[j].trim();
        if (l.endsWith('-->')) {
          parts.push(l.replace(/-->$/, '').trim());
          return parts.join(' ');
        }
        parts.push(l);
      }
    }
  }
  return null;
}

async function walk(relPath) {
  const absPath = path.join(ROOT, relPath);
  const stats = await fs.stat(absPath);
  const name = relPath === '.' ? path.basename(ROOT) : path.basename(relPath);
  if (stats.isDirectory()) {
    const entries = await fs.readdir(absPath);
    const children = [];
    for (const entry of entries) {
      if (IGNORED.has(entry)) continue;
      const childRel = relPath === '.' ? entry : path.posix.join(relPath, entry);
      const child = await walk(childRel);
      if (child) children.push(child);
    }
    children.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === 'dir' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    return {
      name,
      path: relPath,
      kind: 'dir',
      description: dirDescriptions[name] || `${name} directory.`,
      children
    };
  } else if (stats.isFile()) {
    const size = stats.size;
    const ext = path.extname(name).toLowerCase();
    let description = specialDescription(name, relPath) || null;
    let lines;
    if (size <= MAX_FILE_SIZE) {
      const content = await fs.readFile(absPath, 'utf8');
      lines = content.split(/\r?\n/).length;
      const comment = extractLeadingComment(content);
      if (!description && comment) description = comment;
    }
    if (!description) description = defaultDescription(ext);
    const node = {
      name,
      path: relPath,
      kind: 'file',
      description,
      sizeBytes: size
    };
    if (lines !== undefined) node.lines = lines;
    if (languageMap[ext]) node.language = languageMap[ext];
    return node;
  }
  return null;
}

async function generate() {
  const tree = await walk('.');
  const result = {
    metadata: {
      version: 1,
      generatedAt: new Date().toISOString()
    },
    tree
  };
  await fs.writeFile(path.join(ROOT, 'structure.json'), JSON.stringify(result, null, 2));
}

generate().catch(err => {
  console.error(err);
  process.exit(1);
});

