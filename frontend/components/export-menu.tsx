"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Download, FileSpreadsheet, FileJson, FileText, Loader2 } from "lucide-react";

interface ExportMenuProps {
  data: Record<string, any>[];
  columns: string[];
  filename?: string;
}

export function ExportMenu({ data, columns, filename = "query-results" }: ExportMenuProps) {
  const [exporting, setExporting] = useState<string | null>(null);

  const exportCSV = () => {
    setExporting("csv");
    try {
      const headers = columns.join(",");
      const rows = data.map((row) =>
        columns.map((col) => {
          const value = row[col];
          if (value === null || value === undefined) return "";
          // Escape quotes and wrap in quotes if contains comma
          const str = String(value);
          if (str.includes(",") || str.includes('"') || str.includes("\n")) {
            return `"${str.replace(/"/g, '""')}"`;
          }
          return str;
        }).join(",")
      );
      const csv = [headers, ...rows].join("\n");

      downloadFile(csv, `${filename}.csv`, "text/csv");
    } finally {
      setExporting(null);
    }
  };

  const exportJSON = () => {
    setExporting("json");
    try {
      const json = JSON.stringify(data, null, 2);
      downloadFile(json, `${filename}.json`, "application/json");
    } finally {
      setExporting(null);
    }
  };

  const exportExcel = async () => {
    setExporting("excel");
    try {
      // Generate TSV format that Excel can open
      const headers = columns.join("\t");
      const rows = data.map((row) =>
        columns.map((col) => String(row[col] ?? "")).join("\t")
      );
      const tsv = [headers, ...rows].join("\n");

      // Use .xls extension with TSV - Excel will open it correctly
      downloadFile(tsv, `${filename}.xls`, "application/vnd.ms-excel");
    } finally {
      setExporting(null);
    }
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    const headers = columns.join("\t");
    const rows = data.map((row) =>
      columns.map((col) => String(row[col] ?? "")).join("\t")
    );
    const text = [headers, ...rows].join("\n");
    navigator.clipboard.writeText(text);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          {exporting ? (
            <Loader2 className="w-4 h-4 mr-1 animate-spin" />
          ) : (
            <Download className="w-4 h-4 mr-1" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={exportCSV}>
          <FileText className="w-4 h-4 mr-2" />
          Download CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportExcel}>
          <FileSpreadsheet className="w-4 h-4 mr-2" />
          Download Excel
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportJSON}>
          <FileJson className="w-4 h-4 mr-2" />
          Download JSON
        </DropdownMenuItem>
        <DropdownMenuItem onClick={copyToClipboard}>
          <FileText className="w-4 h-4 mr-2" />
          Copy to Clipboard
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
