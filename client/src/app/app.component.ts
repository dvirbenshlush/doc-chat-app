import { Component } from '@angular/core';
import { ChatComponent } from './components/chat/chat.component';
import { DocumentListComponent } from './components/document-list/document-list.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ChatComponent, DocumentListComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  mode = 'groq';

  onModeChange(mode: string) {
    this.mode = mode;
  }
}
