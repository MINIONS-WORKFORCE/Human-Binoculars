// Minimal decoder for the 8-bit grayscale PNGs in api_samples/, so the Node CI job
// can check sizes and pixels without native image libraries.
import { inflateSync } from "node:zlib";

export interface GrayImage {
  width: number;
  height: number;
  colorType: number;
  bitDepth: number;
  pixel(x: number, y: number): number;
}

export function decodeGrayPng(bytes: Uint8Array): GrayImage {
  const data = Buffer.from(bytes);
  if (data.readUInt32BE(0) !== 0x89504e47) throw new Error("Not a PNG");
  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = -1;
  const idat: Buffer[] = [];
  while (offset < data.length) {
    const length = data.readUInt32BE(offset);
    const type = data.toString("ascii", offset + 4, offset + 8);
    const chunk = data.subarray(offset + 8, offset + 8 + length);
    if (type === "IHDR") {
      width = chunk.readUInt32BE(0);
      height = chunk.readUInt32BE(4);
      bitDepth = chunk[8];
      colorType = chunk[9];
    } else if (type === "IDAT") {
      idat.push(chunk);
    }
    offset += 12 + length;
  }
  if (colorType !== 0 || bitDepth !== 8) {
    return { width, height, colorType, bitDepth, pixel: () => Number.NaN };
  }

  // Undo the per-row filters (PNG spec section 9) for one byte per pixel.
  const raw = inflateSync(Buffer.concat(idat));
  const rows = new Uint8Array(width * height);
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (width + 1)];
    for (let x = 0; x < width; x++) {
      const value = raw[y * (width + 1) + 1 + x];
      const left = x > 0 ? rows[y * width + x - 1] : 0;
      const up = y > 0 ? rows[(y - 1) * width + x] : 0;
      const upLeft = x > 0 && y > 0 ? rows[(y - 1) * width + x - 1] : 0;
      let predictor = 0;
      if (filter === 1) predictor = left;
      else if (filter === 2) predictor = up;
      else if (filter === 3) predictor = (left + up) >> 1;
      else if (filter === 4) {
        const p = left + up - upLeft;
        const [pa, pb, pc] = [
          Math.abs(p - left),
          Math.abs(p - up),
          Math.abs(p - upLeft),
        ];
        predictor = pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft;
      }
      rows[y * width + x] = (value + predictor) & 0xff;
    }
  }
  return {
    width,
    height,
    colorType,
    bitDepth,
    pixel: (x, y) => rows[y * width + x],
  };
}
