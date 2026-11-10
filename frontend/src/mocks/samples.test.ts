// Schema check for api_samples/: every sample must satisfy the OpenAPI contract
// the TypeScript types are generated from. Runs in CI next to Đông's Python validator.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Ajv2020 } from "ajv/dist/2020.js";
import { parse } from "yaml";
import { describe, expect, it } from "vitest";
import { decodeGrayPng } from "../test/png";
import { sampleFiles, samplePng, samples } from "./samples";

const openapiPath = fileURLToPath(
  new URL("../../../shared/api-contract/openapi.yaml", import.meta.url),
);
const openapi = parse(readFileSync(openapiPath, "utf8"));

// The whole document is registered so "#/components/schemas/..." refs resolve.
// strict: false lets Ajv skip OpenAPI-only keys such as "paths" and "info".
const ajv = new Ajv2020({
  strict: false,
  allErrors: true,
  validateFormats: false,
});
ajv.addSchema(openapi, "openapi");

describe("api_samples/ JSON matches shared/api-contract/openapi.yaml", () => {
  it.each(sampleFiles)("$file is a valid $schema", ({ schema, json }) => {
    const validate = ajv.getSchema(`openapi#/components/schemas/${schema}`);
    expect(
      validate,
      `schema ${schema} missing from openapi.yaml`,
    ).toBeDefined();
    const valid = validate!(json);
    expect(
      validate!.errors ?? [],
      JSON.stringify(validate!.errors, null, 2),
    ).toEqual([]);
    expect(valid).toBe(true);
  });
});

describe("api_samples/png", () => {
  const { grid, frames } = samples.frames;

  it.each(frames.map((frame, index) => ({ frame, index })))(
    "frame $index and its difference image are $grid.width x $grid.height grayscale",
    ({ index }) => {
      for (const difference of [false, true]) {
        const bytes = samplePng(index, difference);
        expect(
          bytes,
          `frame-${index}${difference ? "_diff" : ""}.png missing`,
        ).toBeDefined();
        const image = decodeGrayPng(bytes!);
        expect({
          width: image.width,
          height: image.height,
          colorType: image.colorType,
          bitDepth: image.bitDepth,
        }).toEqual({
          width: grid.width,
          height: grid.height,
          colorType: 0,
          bitDepth: 8,
        });
      }
    },
  );

  it.each(frames.map((frame, index) => ({ frame, index })))(
    "predicted_px of frame $index lies on the source (PNG top-left origin)",
    ({ frame, index }) => {
      expect(frame.predicted_px).not.toBeNull();
      const [x, y] = frame.predicted_px!;
      const image = decodeGrayPng(samplePng(index, false)!);
      expect(image.pixel(Math.round(x), Math.round(y))).toBeGreaterThanOrEqual(
        200,
      );
    },
  );
});
