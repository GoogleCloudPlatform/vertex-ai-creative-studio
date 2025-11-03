# Use from Library Feature Plan (Revised)

This document outlines the detailed plan for implementing the new "Add from Library" feature. The revised strategy focuses on building and testing the new components in isolation on a dedicated test page before integrating them into the main application.

---

### High-Level Strategy

The goal is to create a reusable `library_chooser_button` component that can be composed with the standard `me.uploader` to allow users to select images from their file system or their Firestore library.

---

### Phase 1: Create the Core "Library Image Selector" Component

- [x] **Create File:** `components/library/library_image_selector.py`.
- [x] **Implement Logic:** Fetches and displays a grid of recent images, calling the `on_select` callback when an image is clicked.

### Phase 2: Create the Reusable "Library Chooser Button" Component

- [x] **Create File:** `components/library/library_chooser_button.py`.
- [x] **Implement Logic:** Renders a button that opens a dialog containing the `library_image_selector`. It accepts an `on_library_select` callback.
- [x] **Delete Old Component:** The monolithic `enhanced_uploader.py` has been deleted.

### Phase 3: Isolated Integration & Testing

- [x] **Create Test Page:** `pages/test_uploader.py`.
- [x] **Implement Test UI:** The test page now demonstrates the `me.uploader` and the `library_chooser_button` both independently and composed together.
- [x] **Register Test Route:** The `/test_uploader` route is registered in `main.py`.
- [x] **Testing Checkpoint:**
    - [x] **(Completed)** Test the standard upload functionality.
    - [x] **(Completed)** Test the "Add from Library" functionality.
        - **Bug:** Dialog was empty. **Fix:** Corrected the data loading pattern in `library_image_selector.py`.
        - **Bug:** Dialog was uncloseable. **Fix:** Added a "Cancel" button.
        - **Bug:** Dialog was too small. **Fix:** Increased dialog dimensions.
        - **Bug:** Callback to parent page was not working. **Fix:** Corrected the event handler to `yield from` the parent's callback.
        - **Bug:** All images in the dialog returned the same URI. **Fix:** Corrected the `lambda` scope issue by switching to a dedicated event handler with a `key`.
        - **Bug:** Multiple instances of the component on the same page had state collisions. **Fix:** Added a `key` to the `library_chooser_button` component and used it to differentiate between instances in the test page's event handler.

### Phase 4: Code Quality and Refinement

- [x] **Review Code:** Review the code in the new component files for adherence to the Google Python Style Guide.
- [x] **Check Docstrings:** Ensure all new functions and components have clear, correctly formatted docstrings.

### Phase 5: Staged Roll-Out to Application Pages

- [ ] **Sub-Phase 5a: Integrate with VTO Page**
    - [ ] Modify `pages/vto.py` to add the `library_chooser_button` next to the person and product image uploaders.
    - [ ] Create and connect the `on_person_image_from_library` and `on_product_image_from_library` callbacks.
    - [ ] **Testing Checkpoint:** Manually test both "Add from Library" buttons on the VTO page.
- [ ] **Sub-Phase 5b: Integrate with Motion Portraits Page**
    - [ ] Analyze `pages/portraits.py` to identify the uploader and state.
    - [ ] Modify the page to add the `library_chooser_button`.
    - [ ] Create and connect the `on_portrait_image_from_library` callback.
    - [ ] **Testing Checkpoint:** Manually test the "Add from Library" button on the Motion Portraits page.
- [ ] **Sub-Phase 5c: Integrate with Product in Scene Page**
    - [ ] Modify `pages/recontextualize.py` to add the `library_chooser_button`.
    - [ ] Create and connect the `on_recontext_source_from_library` callback, ensuring it *appends* to the list of source images.
    - [ ] **Testing Checkpoint:** Manually test the "Add from Library" button on the Product in Scene page.
- [ ] **Sub-Phase 5d: Integrate with Veo i2v Page**
    - [ ] Analyze `pages/veo.py` to identify the i2v uploader and state.
    - [ ] Modify the page to add the `library_chooser_button`.
    - [ ] Create and connect the `on_veo_i2v_from_library` callback.
    - [ ] **Testing Checkpoint:** Manually test the "Add from Library" button on the Veo i2v workflow.
