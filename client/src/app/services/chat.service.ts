import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ChatResponse, Document, Message } from '../models/chat.models';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  sendMessage(question: string, history: Message[]): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
      question,
      history: history.map(m => ({ role: m.role, content: m.content })),
    });
  }

  getDocuments(): Observable<{ documents: Document[] }> {
    return this.http.get<{ documents: Document[] }>(`${this.apiUrl}/documents`);
  }
}
