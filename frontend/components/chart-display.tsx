"use client";

import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BarChart2, LineChart as LineIcon, PieChart as PieIcon, ScatterChart as ScatterIcon } from "lucide-react";

type ChartType = "bar" | "line" | "pie" | "scatter" | "auto";

interface ChartDisplayProps {
  data: Record<string, any>[];
  columns: string[];
  title?: string;
}

const COLORS = [
  "#8884d8",
  "#82ca9d",
  "#ffc658",
  "#ff7c7c",
  "#8dd1e1",
  "#a4de6c",
  "#d0ed57",
  "#ffa07a",
];

export function ChartDisplay({ data, columns, title }: ChartDisplayProps) {
  const [chartType, setChartType] = useState<ChartType>("auto");

  // Detect chart type based on data
  const detectedType = useMemo(() => {
    if (!data || data.length === 0 || columns.length < 2) return "bar";

    const firstCol = columns[0];
    const firstValue = data[0][firstCol];

    // Check if first column looks like a date/time
    const isTimeSeries =
      firstCol.toLowerCase().includes("date") ||
      firstCol.toLowerCase().includes("time") ||
      firstCol.toLowerCase().includes("month") ||
      firstCol.toLowerCase().includes("year") ||
      !isNaN(Date.parse(String(firstValue)));

    if (isTimeSeries) return "line";

    // Check if we have exactly one category and one numeric
    const numericCols = columns.filter((col) =>
      data.every((row) => typeof row[col] === "number" || !isNaN(Number(row[col])))
    );

    if (numericCols.length === 2 && columns.length === 2) return "scatter";
    if (data.length <= 6 && numericCols.length === 1) return "pie";

    return "bar";
  }, [data, columns]);

  const activeType = chartType === "auto" ? detectedType : chartType;

  // Identify category and value columns
  const categoryCol = columns[0];
  const valueCol = columns.length > 1 ? columns[1] : columns[0];
  const valueCols = columns.slice(1).filter((col) =>
    data.every((row) => typeof row[col] === "number" || !isNaN(Number(row[col])))
  );

  // Prepare data for charts
  const chartData = useMemo(() => {
    return data.map((row) => ({
      ...row,
      name: String(row[categoryCol]),
      value: Number(row[valueCol]) || 0,
    }));
  }, [data, categoryCol, valueCol]);

  if (!data || data.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between py-3">
        <CardTitle className="text-base">{title || "Visualization"}</CardTitle>
        <div className="flex gap-1">
          <Button
            variant={activeType === "bar" ? "default" : "outline"}
            size="sm"
            onClick={() => setChartType("bar")}
          >
            <BarChart2 className="w-4 h-4" />
          </Button>
          <Button
            variant={activeType === "line" ? "default" : "outline"}
            size="sm"
            onClick={() => setChartType("line")}
          >
            <LineIcon className="w-4 h-4" />
          </Button>
          <Button
            variant={activeType === "pie" ? "default" : "outline"}
            size="sm"
            onClick={() => setChartType("pie")}
          >
            <PieIcon className="w-4 h-4" />
          </Button>
          <Button
            variant={activeType === "scatter" ? "default" : "outline"}
            size="sm"
            onClick={() => setChartType("scatter")}
          >
            <ScatterIcon className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {activeType === "bar" ? (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                {valueCols.length > 0 ? (
                  valueCols.map((col, i) => (
                    <Bar key={col} dataKey={col} fill={COLORS[i % COLORS.length]} />
                  ))
                ) : (
                  <Bar dataKey="value" fill={COLORS[0]} />
                )}
              </BarChart>
            ) : activeType === "line" ? (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                {valueCols.length > 0 ? (
                  valueCols.map((col, i) => (
                    <Line
                      key={col}
                      type="monotone"
                      dataKey={col}
                      stroke={COLORS[i % COLORS.length]}
                      strokeWidth={2}
                    />
                  ))
                ) : (
                  <Line type="monotone" dataKey="value" stroke={COLORS[0]} strokeWidth={2} />
                )}
              </LineChart>
            ) : activeType === "pie" ? (
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => entry.name}
                >
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            ) : (
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey={columns[0]}
                  name={columns[0]}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  dataKey={columns[1]}
                  name={columns[1]}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <Scatter name="Data" data={chartData} fill={COLORS[0]} />
              </ScatterChart>
            )}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

// Helper to detect if data is chartable
export function isChartable(data: any[], columns: string[]): boolean {
  if (!data || data.length === 0 || columns.length < 2) return false;
  
  // Need at least one numeric column
  const hasNumeric = columns.some((col) =>
    data.every((row) => typeof row[col] === "number" || !isNaN(Number(row[col])))
  );
  
  return hasNumeric && data.length >= 2;
}
