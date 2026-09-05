"use strict";

const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const args = process.argv.slice(2);
const rootIndex = args.indexOf("--root");
const OUTPUT_ROOT =
  rootIndex >= 0 && args[rootIndex + 1]
    ? path.resolve(args[rootIndex + 1])
    : path.resolve(__dirname, "../public");

const COLORS = {
  bg: [0x10, 0x19, 0x2b, 0xff],
  accent: [0xff, 0xbf, 0x47, 0xff],
  light: [0xf7, 0xf8, 0xfb, 0xff]
};

function makeImage(size) {
  const pixels = Buffer.alloc(size * size * 4);
  for (let i = 0; i < size * size; i += 1) {
    const offset = i * 4;
    pixels[offset] = COLORS.bg[0];
    pixels[offset + 1] = COLORS.bg[1];
    pixels[offset + 2] = COLORS.bg[2];
    pixels[offset + 3] = 255;
  }
  return { size, pixels };
}

function setPixel(image, x, y, color) {
  x = Math.floor(x);
  y = Math.floor(y);
  if (x < 0 || y < 0 || x >= image.size || y >= image.size) return;
  const i = (y * image.size + x) * 4;
  image.pixels[i] = color[0];
  image.pixels[i + 1] = color[1];
  image.pixels[i + 2] = color[2];
  image.pixels[i + 3] = color[3];
}

function fillCircle(image, cx, cy, radius, color) {
  const r2 = radius * radius;
  for (let y = Math.floor(cy - radius); y <= Math.ceil(cy + radius); y += 1) {
    for (let x = Math.floor(cx - radius); x <= Math.ceil(cx + radius); x += 1) {
      const dx = x + 0.5 - cx;
      const dy = y + 0.5 - cy;
      if (dx * dx + dy * dy <= r2) setPixel(image, x, y, color);
    }
  }
}

function drawLine(image, x1, y1, x2, y2, thickness, color) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const steps = Math.max(Math.abs(dx), Math.abs(dy), 1);
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    fillCircle(
      image,
      x1 + dx * t,
      y1 + dy * t,
      thickness / 2,
      color
    );
  }
}

function renderIcon(size, maskable = false) {
  const image = makeImage(size);
  const unit = size / 512;
  const compact = maskable ? 0.78 : 1;
  const center = size / 2;
  const radius = 150 * unit * compact;
  const ring = 22 * unit * compact;

  fillCircle(image, center, center, radius, COLORS.accent);
  fillCircle(image, center, center, radius - ring, COLORS.bg);

  drawLine(
    image,
    center,
    center,
    center,
    center - 86 * unit * compact,
    26 * unit * compact,
    COLORS.light
  );
  drawLine(
    image,
    center,
    center,
    center + 72 * unit * compact,
    center + 48 * unit * compact,
    26 * unit * compact,
    COLORS.light
  );
  fillCircle(image, center, center, 18 * unit * compact, COLORS.accent);

  return image;
}

let crcTable = null;
function buildCrcTable() {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
}

function crc32(buffer) {
  if (!crcTable) crcTable = buildCrcTable();
  let c = 0xffffffff;
  for (const byte of buffer) {
    c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuffer = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function encodePng(image) {
  const rowLength = image.size * 4 + 1;
  const raw = Buffer.alloc(rowLength * image.size);
  for (let y = 0; y < image.size; y += 1) {
    const rowOffset = y * rowLength;
    raw[rowOffset] = 0;
    image.pixels.copy(
      raw,
      rowOffset + 1,
      y * image.size * 4,
      (y + 1) * image.size * 4
    );
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(image.size, 0);
  ihdr.writeUInt32BE(image.size, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;

  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
    pngChunk("IEND", Buffer.alloc(0))
  ]);
}

function encodeIco(png, size) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(1, 4);

  const entry = Buffer.alloc(16);
  entry[0] = size;
  entry[1] = size;
  entry.writeUInt16LE(1, 4);
  entry.writeUInt16LE(32, 6);
  entry.writeUInt32LE(png.length, 8);
  entry.writeUInt32LE(22, 12);

  return Buffer.concat([header, entry, png]);
}

function writeBinary(relativePath, buffer) {
  const filePath = path.join(OUTPUT_ROOT, relativePath);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, buffer);
  console.log(`Generated ${relativePath} (${buffer.length} bytes)`);
}

const icon32 = encodePng(renderIcon(32));
writeBinary("favicon.ico", encodeIco(icon32, 32));
writeBinary("apple-touch-icon.png", encodePng(renderIcon(180)));
writeBinary("icons/icon-192.png", encodePng(renderIcon(192)));
writeBinary("icons/icon-512.png", encodePng(renderIcon(512)));
writeBinary("icons/icon-maskable-512.png", encodePng(renderIcon(512, true)));
