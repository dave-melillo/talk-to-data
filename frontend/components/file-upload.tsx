"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, File, Check, Loader2, X } from "lucide-react";

interface UploadStatus {
  status: "idle" | "uploading" | "success" | "error";
  message?: string;
  sourceId?: string;
}

export function FileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ status: "idle" });
  const [preview, setPreview] = useState<any>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setSourceName(selectedFile.name.replace(/\.[^.]+$/, ""));

    // Get preview
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("/api/v1/upload/preview?preview_rows=5", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setPreview(data);
    } catch (error) {
      console.error("Preview failed:", error);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploadStatus({ status: "uploading" });

    const formData = new FormData();
    formData.append("file", file);
    if (sourceName) {
      formData.append("source_name", sourceName);
    }

    try {
      // Upload and normalize in one step
      const res = await fetch("/api/v1/normalize/upload-and-normalize", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Upload failed");
      }

      const data = await res.json();
      setUploadStatus({
        status: "success",
        message: `Successfully imported ${data.row_count} rows`,
        sourceId: data.id,
      });
    } catch (error) {
      setUploadStatus({
        status: "error",
        message: error instanceof Error ? error.message : "Upload failed",
      });
    }
  };

  const handleReset = () => {
    setFile(null);
    setSourceName("");
    setUploadStatus({ status: "idle" });
    setPreview(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Data</CardTitle>
        <CardDescription>
          Upload CSV, Excel, or Parquet files to start querying your data
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!file ? (
          <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted transition-colors">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
              <p className="mb-2 text-sm text-muted-foreground">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-muted-foreground">
                CSV, TSV, Excel (.xlsx), or Parquet (max 100MB)
              </p>
            </div>
            <input
              type="file"
              className="hidden"
              accept=".csv,.tsv,.xlsx,.xls,.parquet,.pq"
              onChange={handleFileChange}
            />
          </label>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <File className="w-8 h-8 text-primary" />
              <div className="flex-1">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleReset}>
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Source Name
              </label>
              <Input
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                placeholder="Enter a name for this data source"
              />
            </div>

            {preview && (
              <div>
                <p className="text-sm font-medium mb-2">
                  Preview ({preview.metadata?.column_count} columns)
                </p>
                <div className="overflow-x-auto border rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        {preview.columns?.map((col: any) => (
                          <th key={col.name} className="p-2 text-left font-medium">
                            {col.name}
                            <span className="text-xs text-muted-foreground ml-1">
                              ({col.inferred_type})
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.data?.map((row: any, i: number) => (
                        <tr key={i} className="border-t">
                          {preview.columns?.map((col: any) => (
                            <td key={col.name} className="p-2">
                              {row[col.name]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {uploadStatus.status === "success" ? (
              <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-lg">
                <Check className="w-5 h-5" />
                <span>{uploadStatus.message}</span>
              </div>
            ) : uploadStatus.status === "error" ? (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-lg">
                <X className="w-5 h-5" />
                <span>{uploadStatus.message}</span>
              </div>
            ) : (
              <Button
                onClick={handleUpload}
                className="w-full"
                disabled={uploadStatus.status === "uploading"}
              >
                {uploadStatus.status === "uploading" ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload and Import
                  </>
                )}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
