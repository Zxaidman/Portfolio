# Images

Drop your files here using these exact names — the page picks them up automatically.
Until a file exists, the page falls back to a coloured gradient (nothing breaks).

```
images/
├── profile.jpg              ← your round profile photo (square crop, ~600×600)
└── projects/
    ├── project-1.jpg        ← project hero images (landscape 4:3, ~1200×900)
    ├── project-2.jpg
    ├── project-3.jpg
    ├── project-4.jpg
    ├── project-5.jpg
    └── project-6.jpg
```

## Changing project names / locations

Edit the `projects` array near the bottom of `index.html`:

```js
{ name:"Project name", location:"Area, City", tag:"Short label", img:"images/projects/project-1.jpg" }
```

Add more objects to the array for more cards — the grid keeps 3 per row automatically.
