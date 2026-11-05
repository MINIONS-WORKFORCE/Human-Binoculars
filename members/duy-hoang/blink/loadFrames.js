// Turn files picked or dropped by the user into frames for the blink viewer.

const isPng = (file) => file.type === "image/png" || /\.png$/i.test(file.name);

// Sorted by name, numbers compared as numbers ("frame-2" before "frame-10"),
// because real frames will be named by observation time.
const byName = (a, b) =>
  a.name.localeCompare(b.name, undefined, { numeric: true });

/**
 * FileList | File[] -> { frames: [{ name, bitmap, width, height }], rejected: [name] }.
 * Files that are not PNG, or that fail to decode, end up in `rejected`.
 */
export async function loadFrames(files) {
  const list = [...files].sort(byName);
  const rejected = list.filter((file) => !isPng(file)).map((file) => file.name);

  const decoded = await Promise.all(
    list.filter(isPng).map(async (file) => {
      try {
        const bitmap = await createImageBitmap(file);
        return {
          name: file.name,
          bitmap,
          width: bitmap.width,
          height: bitmap.height,
        };
      } catch {
        rejected.push(file.name);
        return null;
      }
    }),
  );

  return { frames: decoded.filter(Boolean), rejected };
}

/** Free the memory held by frames that are no longer shown. */
export function releaseFrames(frames) {
  for (const frame of frames) frame.bitmap.close?.();
}
