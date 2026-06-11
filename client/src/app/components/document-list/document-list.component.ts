import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService } from '../../services/chat.service';
import { Document } from '../../models/chat.models';

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './document-list.component.html',
  styleUrl: './document-list.component.scss',
})
export class DocumentListComponent implements OnInit {
  documents: Document[] = [];
  loading = true;

  private topicColors: Record<string, string> = {
    python: '#3b82f6',
    cooking: '#10b981',
    travel: '#f59e0b',
    fitness: '#ef4444',
    finance: '#8b5cf6',
  };

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.chatService.getDocuments().subscribe({
      next: (res) => {
        this.documents = res.documents;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  getColor(docName: string): string {
    const key = Object.keys(this.topicColors).find(k => docName.includes(k));
    return key ? this.topicColors[key] : '#6b7280';
  }

  getIcon(docName: string): string {
    if (docName.includes('python')) return 'code';
    if (docName.includes('cooking')) return 'restaurant';
    if (docName.includes('travel')) return 'flight';
    if (docName.includes('fitness')) return 'fitness_center';
    if (docName.includes('finance')) return 'account_balance';
    return 'description';
  }
}
