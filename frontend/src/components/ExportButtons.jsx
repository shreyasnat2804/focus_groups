import { exportCsvUrl, exportPdfUrl } from "../api";

export default function ExportButtons({ sessionId }) {
  return (
    <div className="export-buttons">
      <a href={exportCsvUrl(sessionId)} download>
        Export CSV
      </a>
      <a href={exportPdfUrl(sessionId)} download>
        Export PDF
      </a>
    </div>
  );
}
