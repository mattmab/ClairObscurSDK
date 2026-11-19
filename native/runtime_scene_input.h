#pragma once
#include <algorithm>
namespace e33_runtime_scene {
// Track each shortcut independently, including releases after authoring exits.
struct GameplayShortcutFilter {
    bool held[3]{};
    bool consume(unsigned key,bool down,bool up,bool enabled){
        const int index=key=='Z'?0:key=='M'?1:key=='G'?2:-1;
        if(index<0)return false;
        if(up && held[index]){held[index]=false;return true;}
        if(down && (held[index] || enabled)){held[index]=true;return true;}
        return false;
    }
};

// Wall-clock controls: short Escape presses never complete a scene. A key held
// before entry or across loss of focus must be released before it can act.
struct StoryPlaybackControls {
    bool f=false,e=false,esc=false,armed=false;
    double escape_since=-1.;
    void begin(bool fp,bool ep,bool escape){f=fp;e=ep;esc=escape;armed=!escape;escape_since=-1.;}
    unsigned key_message(unsigned key,bool down,bool repeat,bool paused){
        if(key!='F' && key!='E')return 0;
        bool& held=key=='F'?f:e;
        const bool edge=down && !held && !repeat;held=down;
        return edge?(key=='F'?(!paused?1U:0U):(paused?2U:0U)):0U;
    }
    unsigned update(double now,bool focused,bool fp,bool ep,bool escape,bool paused){
        if(!focused){begin(fp,ep,escape);armed=false;return 0;}
        unsigned action=0;
        if(fp && !f && !paused)action=1;
        if(ep && !e && paused)action=2;
        f=fp;e=ep;
        if(!escape){escape_since=-1.;armed=true;}
        else if(armed && !esc)escape_since=now;
        esc=escape;
        if(armed && escape_since>=0. && now-escape_since>=3.){action=3;armed=false;escape_since=-1.;}
        return action;
    }
    unsigned progress(double now)const{return escape_since<0.?0:unsigned(std::clamp((now-escape_since)/3.,0.,1.)*15.);}
};

struct StoryInputFilter {
    bool held[256]{};
    bool consume(unsigned key,bool down,bool up,bool active){
        if(key>=256)return false;
        if(up && held[key]){held[key]=false;return true;}
        if(down && (active || held[key])){held[key]=true;return true;}
        return false;
    }
};
}
