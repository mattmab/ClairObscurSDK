    template<class Visit> bool visit_owned_components(uint64_t b,uint64_t actor,Visit&& visit){
        return e33_owned_actor::visit_components(b,actor,visit);
    }
