-- Supabase Storage — `snippets` bucket.
-- Folder layout used by the app (created on demand by uploads, no need to pre-create):
--   speaker_images/<filename>
--   intro_videos/<filename>
--   background_images/<filename>
--   assets/intro_videos/<id>.mp4
--   assets/thumbnails/<id>.png

insert into storage.buckets (id, name, public)
values ('snippets', 'snippets', true)
on conflict (id) do update set public = excluded.public;

-- Public read of any object in the bucket (the app stores public URLs in
-- session.speaker_image_url / intro_video_url / background_image_url and in
-- snippet.storage_link, so anonymous reads must work).
drop policy if exists "snippets public read"     on storage.objects;
drop policy if exists "snippets service write"   on storage.objects;
drop policy if exists "snippets service update"  on storage.objects;
drop policy if exists "snippets service delete"  on storage.objects;

create policy "snippets public read"
    on storage.objects for select
    using (bucket_id = 'snippets');

-- Writes/updates/deletes are made by the backend with the service_role key,
-- which bypasses RLS, so no permissive policies are needed for those.
