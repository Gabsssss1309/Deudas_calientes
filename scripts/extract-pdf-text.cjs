// Standalone script to extract text from a PDF file.
// Called via child_process to avoid Next.js webpack bundling issues with pdf-parse v2.
// Usage: node extract-pdf-text.cjs <path-to-pdf>

const fs = require("fs");

const inputPath = process.argv[2];
if (!inputPath) {
  process.stderr.write("Usage: node extract-pdf-text.cjs <path-to-pdf>");
  process.exit(1);
}

async function main() {
  const { PDFParse } = await import("pdf-parse");
  const buffer = fs.readFileSync(inputPath);
  const parser = new PDFParse({ data: new Uint8Array(buffer) });
  const result = await parser.getText();
  await parser.destroy();
  process.stdout.write(result.text);
}

main().catch((err) => {
  process.stderr.write(err.message || String(err));
  process.exit(1);
});
