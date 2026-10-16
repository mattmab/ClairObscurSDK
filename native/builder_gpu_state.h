    builder_gpu::Bridge gpu_bridge_;
    CallIdentity gpu_actor_{},gpu_capture_{},gpu_target_{};
    uint64_t gpu_actor_lease_=0,gpu_target_lease_=0,gpu_sequence_=0,gpu_pending_=0,gpu_sent_at_=0,gpu_last_capture_=0,gpu_completed_=0;
    uint32_t gpu_error_=0;
    double gpu_last_depth_=0,gpu_last_latency_=0;
    uint64_t gpu_surface_hits_=0;
    struct GpuCandidate {CallIdentity actor,component;double entry;};
    std::vector<GpuCandidate> gpu_candidates_;
    struct GpuPending {uint64_t request,sent;CallIdentity actor,component;bool scene;};
    std::vector<GpuPending> gpu_flights_;
    size_t gpu_next_=0;
    bool gpu_query_active_=false,gpu_scene_pending_=false,gpu_query_stale_=false;
    double gpu_origin_[3]{},gpu_dir_[3]{},gpu_best_distance_=200000.,gpu_query_limit_=200000.,gpu_ready_origin_[3]{},gpu_ready_point_[3]{};
    CallIdentity gpu_best_actor_{},gpu_best_component_{},gpu_pending_actor_{},gpu_pending_component_{},gpu_ready_actor_{},gpu_ready_component_{};
    uint64_t gpu_ready_time_=0;

    double gpu_samples_[48]{};
    size_t gpu_sample_cursor_=0;

    CallIdentity gpu_preferred_component_{};
    double gpu_scene_depth_=0.;

    uint64_t gpu_query_started_=0;

    bool gpu_click_active_=false,gpu_click_empty_=false;
    double gpu_click_origin_[3]{},gpu_click_dir_[3]{};
