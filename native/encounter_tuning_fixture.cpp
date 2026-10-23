#include "encounter_tuning_policy.h"
#include <cassert>
#include <limits>
int main(){
    using namespace e33_encounter_tuning;
    Settings s;assert(s.valid()&&s.defaults());s.level_mode=1;s.level=10;
    assert(level_for(s,30)==40&&level_for(s,95)==99);s.level=-98;assert(level_for(s,5)==1);
    s.level_mode=2;s.level=55;assert(level_for(s,20)==55);s.health=std::numeric_limits<double>::quiet_NaN();assert(!s.valid());
    s.health=2;s.difficulty=3;assert(!s.valid());s.difficulty=2;assert(s.valid());
    s.health=1000;assert(s.valid());s.health=1000.01;assert(!s.valid());
    s.health=std::numeric_limits<double>::infinity();assert(!s.valid());
    ScalarOverride<int> level;int current=20;
    for(int i=0;i<10;++i){auto base=level.baseline(current);level.set(current,base+5);assert(current==25);}
    level.restore(current);assert(current==20);
    level.set(current,50);current=65;level.restore(current);assert(current==65);
    ScalarOverride<double> hp;double h=0;hp.set(h,2);hp.restore(h);assert(h==0);
    // Abandon empties the roster before the retry decision. Restore effects
    // once while idle; do not disable the next original initialization.
    RetryLifetime retry;ScalarOverride<int> retry_level;ScalarOverride<double> retry_hp;
    int authored_level=60;double authored_hp=0;
    assert(retry.accepts_call()&&!retry.battle_observed()&&!retry.observe_idle());
    for(int attempt=0;attempt<3;++attempt){
        assert(retry.accepts_call());retry.observe_owned_call();
        for(int enemy=0;enemy<3;++enemy){
            auto baseline=retry_level.baseline(authored_level);
            retry_level.set(authored_level,baseline+10);
            auto health_baseline=retry_hp.baseline(authored_hp);
            retry_hp.set(authored_hp,(health_baseline>0?health_baseline:1.)*1000.);
            assert(authored_level==70&&authored_hp==1000.);
        }
        assert(retry.battle_observed()&&!retry.restored()&&retry.observe_idle());
        // Engine-authored reset is preserved; our remaining write is restored.
        authored_level=0;retry_level.restore(authored_level);retry_hp.restore(authored_hp);
        assert(authored_level==0&&authored_hp==0&&retry.restored()&&retry.accepts_call());
        assert(!retry.observe_idle());authored_level=60;
    }
    retry.close();assert(!retry.accepts_call()&&retry.restored()&&!retry.observe_idle());
    retry.observe_owned_call();assert(!retry.accepts_call());
    return 0;
}
