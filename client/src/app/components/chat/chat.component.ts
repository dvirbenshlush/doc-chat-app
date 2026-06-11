import { AfterViewChecked, Component, ElementRef, EventEmitter, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { ChatService } from '../../services/chat.service';
import { Message } from '../../models/chat.models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatCardModule,
    MatExpansionModule,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements AfterViewChecked {
  @Output() modeChange = new EventEmitter<string>();
  @ViewChild('messageContainer') private messageContainer!: ElementRef;

  messages: Message[] = [];
  inputText = '';
  isLoading = false;

  constructor(private chatService: ChatService) {}

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  sendMessage() {
    const question = this.inputText.trim();
    if (!question || this.isLoading) return;

    this.inputText = '';
    this.messages.push({ role: 'user', content: question, timestamp: new Date() });
    this.isLoading = true;

    this.chatService.sendMessage(question, this.messages).subscribe({
      next: (response) => {
        this.messages.push({
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date(),
          sql_query: response.sql_query,
          results: response.results,
          route: response.route,
        });
        this.modeChange.emit(response.mode);
        this.isLoading = false;
      },
      error: () => {
        this.messages.push({
          role: 'assistant',
          content: 'Something went wrong. Please check that the server is running on port 8000.',
          timestamp: new Date(),
        });
        this.isLoading = false;
      },
    });
  }

  onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  getColumns(results: any[]): string[] {
    if (!results || results.length === 0) return [];
    return Object.keys(results[0]);
  }

  private scrollToBottom() {
    try {
      const el = this.messageContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch {}
  }
}
