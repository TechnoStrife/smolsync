
## smolsync

My pet project for offline synchronization of multiple directories 
across multiple devices
with custom gitignore-like ignore rules

I got tired of synchronizing data across my devices, and 
I also don't want to upload it all to the cloud because
there may be a lot of extra files like `node_modules` or 
`__pycache__`, and also some files may be quite big and
would use a lot of space

smolsync would allow me to save the state of my directories,
copy only new and modified files to a new location or a zip archive 
that I can easily transfer to other devices

Then somlsync would analyze that archive, 
determine what changes were made on the previous device,
and make the same changes on the current device: 
add, modify, move or delete the files, 
displaying what changes cannot be reproduced

Possible uses include: sharing code that is not uploaded to GitHub,
copying new and modified documents, music, pictures and videos to other devices
