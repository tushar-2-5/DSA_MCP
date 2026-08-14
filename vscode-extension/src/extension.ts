import * as vscode from 'vscode';
import { RecallApiClient } from './apiClient';
import { MasteryProvider } from './masteryProvider';
import { registerCommands } from './commands';

export async function activate(context: vscode.ExtensionContext) {
    const apiClient = new RecallApiClient();
    const masteryProvider = new MasteryProvider(apiClient);

    vscode.window.registerTreeDataProvider('recallMastery', masteryProvider);
    registerCommands(context, apiClient, masteryProvider);

    const config = vscode.workspace.getConfiguration('recall');
    const notifyOnStartup = config.get<boolean>('notifyOnStartup', true);

    if (notifyOnStartup) {
        try {
            const topics = await apiClient.getMastery();
            if (topics && topics.length > 0) {
                const weakTopics = topics.filter(t => t.mastery_score < 0.30);
                for (const t of weakTopics) {
                    const topicName = t.slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const scorePct = Math.round(t.mastery_score * 100);
                    vscode.window.showWarningMessage(
                        `Recall: You need to practice ${topicName}! Score: ${scorePct}%`,
                        "Get Study Plan"
                    ).then(selection => {
                        if (selection === "Get Study Plan") {
                            vscode.commands.executeCommand("recall.getStudyPlan");
                        }
                    });
                }
            }
        } catch (err) {
            console.error("Error during Recall startup notification check:", err);
        }
    }
}

export function deactivate() {}
