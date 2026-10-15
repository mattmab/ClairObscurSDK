#include <cmath>
#include <algorithm>
#include <vector>
#include <cstdint>
#include <cassert>
struct CallIdentity {int index,serial;uint64_t address;};
uint64_t call_identity(uint64_t,CallIdentity c){return c.address;}
struct Test {
struct Candidate {CallIdentity actor,component;double low[3],high[3],pose[12];};
std::vector<Candidate> candidates_;double position_[3]{};
    static void inverse_rotate(const double* q,const double* v,double* out) {
        const double t[]={-2*(q[1]*v[2]-q[2]*v[1]),-2*(q[2]*v[0]-q[0]*v[2]),-2*(q[0]*v[1]-q[1]*v[0])};
        out[0]=v[0]+q[3]*t[0]-q[1]*t[2]+q[2]*t[1];
        out[1]=v[1]+q[3]*t[1]-q[2]*t[0]+q[0]*t[2];
        out[2]=v[2]+q[3]*t[2]-q[0]*t[1]+q[1]*t[0];
    }
    void bounds_pick(uint64_t b,const double* rayOrigin,const double* dir,CallIdentity& actor,CallIdentity& component,double& distance) {
        for(const auto& c:candidates_) {
            double relative[3];for(int j=0;j<3;++j)relative[j]=rayOrigin[j]-c.pose[4+j];
            double origin[3],direction[3];inverse_rotate(c.pose,relative,origin);inverse_rotate(c.pose,dir,direction);
            double entryDistance=0,exitDistance=distance;bool valid=true;
            for(int j=0;j<3;++j) {
                origin[j]/=c.pose[8+j];direction[j]/=c.pose[8+j];
                if(std::abs(direction[j])<1.e-10){if(origin[j]<c.low[j]||origin[j]>c.high[j])valid=false;continue;}
                double a=(c.low[j]-origin[j])/direction[j],z=(c.high[j]-origin[j])/direction[j];if(a>z)std::swap(a,z);
                entryDistance=std::max(entryDistance,a);exitDistance=std::min(exitDistance,z);if(entryDistance>exitDistance)valid=false;
            }
            if(!valid||entryDistance<1.||entryDistance>=distance||!call_identity(b,c.actor)||!call_identity(b,c.component))continue;
            actor=c.actor;component=c.component;distance=entryDistance;
        }
    }
};
int main(){
 Test t; Test::Candidate c{};c.actor={1,1,1};c.component={2,1,2};
 for(int j=0;j<3;++j){c.low[j]=-1;c.high[j]=1;c.pose[8+j]=1;}
 c.pose[3]=1;c.pose[4]=10;t.candidates_.push_back(c);
 double dir[]={1,0,0},distance=100;CallIdentity actor{},component{};
 t.bounds_pick(0,t.position_,dir,actor,component,distance);assert(component.address==2&&std::abs(distance-9)<1e-9);
 actor={};component={};distance=5;t.bounds_pick(0,t.position_,dir,actor,component,distance);assert(!component.address&&distance==5);
 t.position_[1]=3;distance=100;t.bounds_pick(0,t.position_,dir,actor,component,distance);assert(!component.address);
 t.position_[1]=0;t.candidates_[0].pose[2]=std::sqrt(.5);t.candidates_[0].pose[3]=std::sqrt(.5);
 t.candidates_[0].high[1]=4;distance=100;t.bounds_pick(0,t.position_,dir,actor,component,distance);assert(component.address==2&&std::abs(distance-6)<1e-8);
 double independentOrigin[]={0,0,0};t.position_[1]=100;actor={};component={};distance=100;
 t.bounds_pick(0,independentOrigin,dir,actor,component,distance);assert(component.address==2&&std::abs(distance-6)<1e-8);
 t.position_[1]=0;
 t.position_[0]=10;actor={};component={};distance=100;t.bounds_pick(0,t.position_,dir,actor,component,distance);assert(!component.address);
}
