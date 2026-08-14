import * as vscode from 'vscode';
import { RecallApiClient } from './apiClient';
import { MasteryProvider } from './masteryProvider';

export function registerCommands(
    context: vscode.ExtensionContext,
    apiClient: RecallApiClient,
    masteryProvider: MasteryProvider
) {
    const outputChannel = vscode.window.createOutputChannel("Recall Study Plan");

    context.subscriptions.push(
        vscode.commands.registerCommand('recall.showMastery', () => {
            vscode.commands.executeCommand('recallMastery.focus');
        }),

        vscode.commands.registerCommand('recall.getStudyPlan', async () => {
            const config = vscode.workspace.getConfiguration('recall');
            const company = config.get<string>('targetCompany', 'amazon');
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: `Fetching Recall Study Plan for ${company}...`
            }, async () => {
                const plan = await apiClient.getStudyPlan(company);
                if (plan) {
                    outputChannel.clear();
                    outputChannel.appendLine(plan);
                    outputChannel.show(true);
                } else {
                    vscode.window.showErrorMessage("Failed to fetch Recall Study Plan.");
                }
            });
        }),

        vscode.commands.registerCommand('recall.logAttempt', async () => {
            const title = await vscode.window.showInputBox({
                prompt: "Enter Problem Title (e.g. Two Sum)",
                placeHolder: "Two Sum"
            });
            if (!title) { return; }

            const outcomePick = await vscode.window.showQuickPick(
                ["PASS", "PARTIAL", "FAIL"],
                { placeHolder: "Select Outcome" }
            );
            if (!outcomePick) { return; }

            const timeStr = await vscode.window.showInputBox({
                prompt: "Time taken in minutes",
                placeHolder: "20"
            });
            const timeTaken = timeStr ? parseInt(timeStr, 10) || 0 : 0;

            const success = await apiClient.logAttempt(title, outcomePick, timeTaken);
            if (success) {
                vscode.window.showInformationMessage("Attempt logged successfully!");
                masteryProvider.refresh();
            } else {
                vscode.window.showErrorMessage("Failed to log attempt. Check settings or network.");
            }
        }),

        vscode.commands.registerCommand('recall.setTargetCompany', async () => {
            const currentCompany = vscode.workspace.getConfiguration('recall').get<string>('targetCompany', 'amazon');
            const company = await vscode.window.showInputBox({
                prompt: "Enter target company for interview prep",
                value: currentCompany
            });
            if (company !== undefined) {
                await vscode.workspace.getConfiguration('recall').update('targetCompany', company.trim(), vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage(`Target company set to: ${company}`);
            }
        }),

        vscode.commands.registerCommand('recall.refresh', () => {
            masteryProvider.refresh();
        })
    );
}
