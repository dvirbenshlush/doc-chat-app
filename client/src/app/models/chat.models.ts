export interface Source {
  doc: string;
  excerpt: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
  sql_query?: string | null;
  results?: any[];
  route?: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  mode: string;
  sql_query?: string | null;
  results?: any[];
  route?: string;
}

export interface Document {
  name: string;
  display_name: string;
}

export interface TableColumn {
  name: string;
  type: string;
}

export interface TableInfo {
  name: string;
  row_count: number;
  columns: TableColumn[];
}
