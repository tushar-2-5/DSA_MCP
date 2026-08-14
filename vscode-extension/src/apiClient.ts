import * as vscode from 'vscode';

export interface MasteryTopic {
    slug: string;
    mastery_score: number;
    last_practiced_at?: string | null;
}

export class RecallApiClient {
    private get serverUrl(): string {
        const config = vscode.workspace.getConfiguration('recall');
        let url = config.get<string>('serverUrl', 'https://web-production-54438.up.railway.app');
        return url.replace(/\/+$/, '');
    }

    private get userEmail(): string {
        const config = vscode.workspace.getConfiguration('recall');
        const email = config.get<string>('userEmail', '').trim();
        return email || 'alex@recall.dev';
    }


    public async getMastery(): Promise<MasteryTopic[] | null> {
        try {
            const email = this.userEmail;
            const url = `${this.serverUrl}/api/mastery?email=${encodeURIComponent(email)}`;
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`Recall API getMastery failed: ${response.statusText}`);
                return null;
            }
            const data = (await response.json()) as any;
            return data.topics || [];
        } catch (error) {
            console.error('Recall API getMastery error:', error);
            return null;
        }
    }

    public async getStudyPlan(company: string): Promise<string | null> {
        try {
            const email = this.userEmail;
            const url = `${this.serverUrl}/api/suggest?email=${encodeURIComponent(email)}&company=${encodeURIComponent(company)}`;
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`Recall API getStudyPlan failed: ${response.statusText}`);
                return null;
            }
            const data = (await response.json()) as any;
            if (typeof data === 'string') {
                return data;
            }
            if (data.reason || data.recommendation) {
                const rec = data.recommendation ? `${data.recommendation.title} (${data.recommendation.difficulty})` : 'None';
                return `Recall Study Plan for ${company.toUpperCase()}:\nTargeted Topic: ${data.targeted_topic}\nRecommendation: ${rec}\nReason: ${data.reason}`;
            }
            return JSON.stringify(data, null, 2);
        } catch (error) {
            console.error('Recall API getStudyPlan error:', error);
            return null;
        }
    }

    public async logAttempt(problemTitle: string, outcome: string, timeTakenMinutes: number): Promise<boolean> {
        try {
            const email = this.userEmail;
            const url = `${this.serverUrl}/api/log-attempt`;
            const payload = {
                email: email,
                problem_title: problemTitle,
                outcome: outcome.toLowerCase(),
                time_taken_minutes: timeTakenMinutes
            };
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) {
                console.error(`Recall API logAttempt failed: ${response.statusText}`);
                return false;
            }
            return true;
        } catch (error) {
            console.error('Recall API logAttempt error:', error);
            return false;
        }
    }
}
