import catalogue from "../../backend/data/catalogue.json";

// Read the complete public catalogue on the server, independently of UI filters.
export const songTitles = catalogue.works.map(work => work.title);

function csvField(value: string) {
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

export const songTitlesCsv = "\uFEFF" + ["曲名", ...songTitles].map(csvField).join("\r\n") + "\r\n";
