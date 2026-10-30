#pragma once
namespace e33_timeline_blueprint {
enum class RevealResult {Rejected,Complete,Unknown};
struct RevealJournal {bool attempted=false;};
// Consumers validate owned class/world identities and exact engine profiles.
// Never replay a partially completed reveal or reset before acknowledged close.
template<class Admit,class Collision,class Tick,class Show,class Verify>
RevealResult reveal(RevealJournal& journal,Admit admit,Collision collision,
                    Tick tick,Show show,Verify verify) {
    if(journal.attempted||!admit())return RevealResult::Rejected;
    journal.attempted=true;
    if(!collision()||!tick()||!show()||!verify())return RevealResult::Unknown;
    return RevealResult::Complete;
}
}
