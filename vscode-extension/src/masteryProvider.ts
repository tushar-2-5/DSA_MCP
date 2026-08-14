import * as vscode from 'vscode';
import { RecallApiClient } from './apiClient';

export class MasteryItem extends vscode.TreeItem {
    constructor(
        public readonly topic: string,
        public readonly score: number
    ) {
        let emoji = '🔴';
        if (score >= 0.60) {
            emoji = '🟢';
        } else if (score >= 0.30) {
            emoji = '🟡';
        }

        const scorePct = Math.round(score * 100);
        const label = `${emoji} ${topic}: ${scorePct}%`;

        super(label, vscode.TreeItemCollapsibleState.None);
        this.tooltip = `Topic: ${topic} | Mastery: ${scorePct}%`;
        this.contextValue = 'masteryItem';
    }
}

export class MasteryProvider implements vscode.TreeDataProvider<MasteryItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<MasteryItem | undefined | null | void> = new vscode.EventEmitter<MasteryItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<MasteryItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private apiClient: RecallApiClient) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: MasteryItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: MasteryItem): Promise<MasteryItem[]> {
        if (element) {
            return [];
        }
        const topics = await this.apiClient.getMastery();
        if (!topics || topics.length === 0) {
            return [];
        }
        return topics.map(t => {
            const topicName = t.slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            return new MasteryItem(topicName, t.mastery_score);
        });
    }
}
