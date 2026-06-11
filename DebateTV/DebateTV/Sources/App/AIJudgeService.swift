import Foundation


@Observable
final class AIJudgeService {
    var isJudging: Bool = false


    func judgeDebate(topic: DebateTopic, userArguments: [String], opponentArguments: [String]) async -> DebateResult {
        isJudging = true
        defer { isJudging = false }


        try? await Task.sleep(for: .seconds(2.5))


        let userScore = Int.random(in: 55...95)
        let opponentScore = Int.random(in: 45...90)


        let outcome: DebateOutcome
        if userScore > opponentScore + 5 {
            outcome = .win
        } else if opponentScore > userScore + 5 {
            outcome = .loss
        } else {
            outcome = .draw
        }


        let reasonings = [
            "The winning side demonstrated superior logical reasoning with well-structured arguments, effectively countering opposition points while maintaining composure throughout the debate.",
            "A close match where both sides made compelling cases. The edge went to the debater who provided more concrete evidence and avoided logical fallacies.",
            "Strong rhetorical skills on display. The decisive factor was the ability to directly address counter-arguments rather than deflecting.",
            "Both debaters showed deep understanding of the topic. The margin came from the more effective use of real-world examples and analogies.",
        ]


        let strongArgs = [
            "Effectively framed the core issue with a compelling opening thesis that set the tone for the entire debate.",
            "Used a powerful historical parallel that clearly illustrated the argument's real-world implications.",
            "Presented a nuanced cost-benefit analysis that accounted for multiple stakeholder perspectives.",
            "Built a logical chain of reasoning that was difficult for the opponent to dismantle."
        ]
        
        let weakArgs = [
            "Struggled to articulate a clear defense when presented with contradictory evidence.",
            "Relied too heavily on emotional appeals rather than substantive facts in the closing statement."
        ]
        
        return DebateResult(
            topic: topic.title,
            outcome: outcome,
            userScore: userScore,
            opponentScore: opponentScore,
            reasoning: reasonings.randomElement()!,
            strongArguments: [strongArgs.randomElement()!],
            weakArguments: [weakArgs.randomElement()!]
        )
    }
}