#pragma once
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
}
