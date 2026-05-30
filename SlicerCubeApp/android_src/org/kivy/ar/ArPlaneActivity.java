package org.kivy.ar;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.content.res.ColorStateList;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.FrameLayout;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import com.google.ar.core.Anchor;
import com.google.ar.core.ArCoreApk;
import com.google.ar.core.Camera;
import com.google.ar.core.Config;
import com.google.ar.core.Frame;
import com.google.ar.core.HitResult;
import com.google.ar.core.Plane;
import com.google.ar.core.Session;
import com.google.ar.core.Trackable;
import com.google.ar.core.TrackingState;
import com.google.ar.core.exceptions.CameraNotAvailableException;
import com.google.ar.core.exceptions.UnavailableApkTooOldException;
import com.google.ar.core.exceptions.UnavailableArcoreNotInstalledException;
import com.google.ar.core.exceptions.UnavailableDeviceNotCompatibleException;
import com.google.ar.core.exceptions.UnavailableSdkTooOldException;
import com.google.ar.core.exceptions.UnavailableUserDeclinedInstallationException;
import com.google.ar.sceneform.AnchorNode;
import com.google.ar.sceneform.ArSceneView;
import com.google.ar.sceneform.Node;
import com.google.ar.sceneform.math.Quaternion;
import com.google.ar.sceneform.math.Vector3;
import com.google.ar.sceneform.rendering.MaterialFactory;
import com.google.ar.sceneform.rendering.ModelRenderable;
import com.google.ar.sceneform.rendering.ShapeFactory;
import com.google.ar.sceneform.rendering.ViewRenderable;

import org.json.JSONArray;
import org.json.JSONObject;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class ArPlaneActivity extends Activity {
    private static final int CAMERA_PERMISSION_CODE = 8021;
    private static final int SCALE_BAR_COLOR = Color.rgb(0x87, 0xC4, 0xE9);
    private static final int SCALE_THUMB_COLOR = Color.rgb(0x4F, 0x8F, 0xB3);
    private static final float SPLIT_OFFSET_METERS = 0.055f;
    private static final float CUBE_SIDE_METERS = 0.20f;
    private static final float HALF_SIDE = CUBE_SIDE_METERS / 2.0f;
    private static final float AR_BASE_SCALE = 0.5f;
    private static final int SCALE_MIN_PERCENT = 20;
    private static final int SCALE_BAR_MAX = 480;
    private static final int DEFAULT_SCALE_PROGRESS = 80;
    private static final float MIN_LINE_LENGTH = 0.0005f;
    private static final float UNIQUE_POINT_DISTANCE_SQ = 0.000001f;
    private static final String STATUS_SCANNING = "START SCANNING FOR A FLAT SURFACE";

    private static final float[][] CUBE_VERTICES = new float[][]{
            {-1.0f, -1.0f, -1.0f},
            {-1.0f, -1.0f,  1.0f},
            {-1.0f,  1.0f, -1.0f},
            {-1.0f,  1.0f,  1.0f},
            { 1.0f, -1.0f, -1.0f},
            { 1.0f, -1.0f,  1.0f},
            { 1.0f,  1.0f, -1.0f},
            { 1.0f,  1.0f,  1.0f}
    };

    private static final int[][] CUBE_EDGES = new int[][]{
            {0, 1}, {0, 2}, {0, 4},
            {3, 1}, {3, 2}, {3, 7},
            {5, 1}, {5, 4}, {5, 7},
            {6, 2}, {6, 4}, {6, 7}
    };

    private ArSceneView arSceneView;
    private Session arSession;
    private boolean installRequested;

    private ModelRenderable edgeLineRenderable;
    private ModelRenderable sectionLineRenderable;
    private ModelRenderable sectionPointRenderable;
    private ModelRenderable sectionSurfaceFillRenderable;
    private ModelRenderable splitSurfaceGuideRenderable;

    private AnchorNode anchorNode;
    private Node cubeNode;
    private Anchor currentAnchor;

    private TextView statusText;
    private TextView scaleValueText;
    private SeekBar scaleSeekBar;
    private Button splitButton;

    private float objectScale = 1.0f;
    private boolean objectPlaced = false;
    private boolean splitMode = false;
    private Typeface appTypeface;

    private Node rotationNode;
    private boolean isDraggingCube = false;
    private float lastTouchX = 0.0f;
    private float lastTouchY = 0.0f;
    private static final float ROTATION_SENSITIVITY = 0.35f;

    private final ArrayList<Vector3> crossSectionPoints = new ArrayList<>();
    private final ArrayList<Node> visualNodes = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        installRequested = false;
        loadAppTypeface();
        loadCubePayloadFromIntent();
        buildLayout();
        buildRenderables();
    }

    private void loadAppTypeface() {
        try {
            appTypeface = Typeface.createFromAsset(getAssets(), "fonts/Viga-Regular.ttf");
        } catch (Exception ignored) {
            appTypeface = null;
        }
    }

    private void applyAppFont(TextView view) {
        if (view != null && appTypeface != null) {
            try {
                view.setTypeface(appTypeface);
            } catch (Exception ignored) { }
        }
    }

    private void buildLayout() {
        FrameLayout root = new FrameLayout(this);

        arSceneView = new ArSceneView(this);
        root.addView(
                arSceneView,
                new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.MATCH_PARENT
                )
        );

        statusText = new TextView(this);
        statusText.setText(STATUS_SCANNING);
        applyAppFont(statusText);
        statusText.setTextColor(Color.WHITE);
        statusText.setTextSize(16.0f);
        statusText.setGravity(Gravity.CENTER);
        statusText.setShadowLayer(4.0f, 1.0f, 1.0f, Color.BLACK);
        statusText.setBackgroundColor(0x66000000);
        statusText.setPadding(dp(10), dp(8), dp(10), dp(8));
        FrameLayout.LayoutParams statusParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        statusParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        statusParams.setMargins(dp(8), dp(14), dp(8), 0);
        statusText.setVisibility(View.VISIBLE);
        root.addView(statusText, statusParams);

        LinearLayout bottomControls = new LinearLayout(this);
        bottomControls.setOrientation(LinearLayout.VERTICAL);
        bottomControls.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams bottomParams = new FrameLayout.LayoutParams(dp(260), FrameLayout.LayoutParams.WRAP_CONTENT);
        bottomParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        bottomParams.setMargins(0, 0, 0, dp(14));
        root.addView(bottomControls, bottomParams);

        splitButton = makeControlButton("SPLIT", v -> toggleSplitMode());
        LinearLayout.LayoutParams splitParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44));
        splitParams.setMargins(0, 0, 0, dp(8));
        bottomControls.addView(splitButton, splitParams);
        updateSplitButtonText();

        Button resetButton = makeControlButton("RESET CUBE PLACEMENT", v -> resetObject());
        LinearLayout.LayoutParams resetParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44));
        resetParams.setMargins(0, 0, 0, dp(8));
        bottomControls.addView(resetButton, resetParams);

        Button closeButton = makeControlButton("EXIT AR MODE", v -> finish());
        LinearLayout.LayoutParams closeParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44));
        bottomControls.addView(closeButton, closeParams);

        FrameLayout scalePanel = new FrameLayout(this);
        scalePanel.setBackgroundColor(Color.TRANSPARENT);
        FrameLayout.LayoutParams scalePanelParams = new FrameLayout.LayoutParams(dp(84), dp(380));
        scalePanelParams.gravity = Gravity.RIGHT | Gravity.CENTER_VERTICAL;
        scalePanelParams.setMargins(0, 0, dp(6), 0);
        root.addView(scalePanel, scalePanelParams);

        FrameLayout scaleBox = new FrameLayout(this);
        scaleBox.setBackground(makeRoundedBackground(0xEFFFFFFF, Color.BLACK, dp(1), dp(18)));
        FrameLayout.LayoutParams scaleBoxParams = new FrameLayout.LayoutParams(dp(72), dp(360));
        scaleBoxParams.gravity = Gravity.CENTER;
        scalePanel.addView(scaleBox, scaleBoxParams);

        TextView scaleLabel = new TextView(this);
        scaleLabel.setText("S\nC\nA\nL\nE");
        applyAppFont(scaleLabel);
        scaleLabel.setTextColor(Color.WHITE);
        scaleLabel.setTextSize(14.0f);
        scaleLabel.setGravity(Gravity.CENTER);
        scaleLabel.setBackground(makeRoundedBackground(0xEE111111, SCALE_BAR_COLOR, dp(1), dp(5)));
        FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(dp(38), dp(96));
        labelParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        labelParams.topMargin = dp(8);
        scaleBox.addView(scaleLabel, labelParams);

        FrameLayout barFrame = new FrameLayout(this);
        barFrame.setBackground(makeRoundedBackground(0x00FFFFFF, Color.TRANSPARENT, 0, dp(8)));
        FrameLayout.LayoutParams barFrameParams = new FrameLayout.LayoutParams(dp(46), dp(198));
        barFrameParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        barFrameParams.topMargin = dp(112);
        scaleBox.addView(barFrame, barFrameParams);

        scaleSeekBar = new SeekBar(this);
        scaleSeekBar.setMax(SCALE_BAR_MAX);
        scaleSeekBar.setProgress(DEFAULT_SCALE_PROGRESS);
        scaleSeekBar.setRotation(-90.0f);
        scaleSeekBar.setPadding(0, 0, 0, 0);
        styleScaleSeekBar(scaleSeekBar);
        scaleSeekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                int percent = SCALE_MIN_PERCENT + progress;
                objectScale = percent / 100.0f;
                scaleValueText.setText(percent + "%");
                applyObjectScale();
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) { }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) { }
        });
        FrameLayout.LayoutParams seekParams = new FrameLayout.LayoutParams(dp(196), dp(44));
        seekParams.gravity = Gravity.CENTER;
        barFrame.addView(scaleSeekBar, seekParams);

        scaleValueText = new TextView(this);
        scaleValueText.setText("100%");
        applyAppFont(scaleValueText);
        scaleValueText.setTextColor(Color.WHITE);
        scaleValueText.setTextSize(15.0f);
        scaleValueText.setGravity(Gravity.CENTER);
        scaleValueText.setBackground(makeRoundedBackground(0xEE111111, Color.BLACK, dp(1), dp(4)));
        FrameLayout.LayoutParams valueParams = new FrameLayout.LayoutParams(dp(52), dp(30));
        valueParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        valueParams.bottomMargin = dp(10);
        scaleBox.addView(scaleValueText, valueParams);

        setContentView(root);

        arSceneView.getScene().setOnTouchListener((hitTestResult, motionEvent) -> {
            if (objectPlaced) {
                handleCubeDragRotation(motionEvent);
                return true;
            }

            if (motionEvent.getAction() == MotionEvent.ACTION_UP) {
                handleTap(motionEvent);
                return true;
            }
            return true;
        });

        arSceneView.getScene().addOnUpdateListener(frameTime -> updateStatusFromTracking());
    }

    private Button makeControlButton(String text, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(text);
        applyAppFont(button);
        button.setTextColor(Color.BLACK);
        button.setBackgroundColor(Color.WHITE);
        button.setOnClickListener(listener);
        return button;
    }

    private void styleScaleSeekBar(SeekBar seekBar) {
        try {
            ColorStateList barTint = ColorStateList.valueOf(SCALE_BAR_COLOR);
            ColorStateList thumbTint = ColorStateList.valueOf(SCALE_THUMB_COLOR);
            if (seekBar.getProgressDrawable() != null) {
                seekBar.getProgressDrawable().setTintList(barTint);
            }
            if (seekBar.getThumb() != null) {
                seekBar.getThumb().setTintList(thumbTint);
            }
        } catch (Exception ignored) { }
    }

    private GradientDrawable makeRoundedBackground(int fillColor, int strokeColor, int strokeWidth, int radius) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setShape(GradientDrawable.RECTANGLE);
        drawable.setColor(fillColor);
        drawable.setStroke(strokeWidth, strokeColor);
        drawable.setCornerRadius(radius);
        return drawable;
    }

    private void buildRenderables() {
        MaterialFactory.makeOpaqueWithColor(
                this,
                new com.google.ar.sceneform.rendering.Color(0.02f, 0.02f, 0.02f, 1.0f)
        ).thenAccept(material -> {
            edgeLineRenderable = ShapeFactory.makeCylinder(
                    0.0045f,
                    1.0f,
                    new Vector3(0.0f, 0.0f, 0.0f),
                    material
            );
        }).exceptionally(throwable -> {
            toast("Could not create cube edges: " + throwable.getMessage());
            return null;
        });

        MaterialFactory.makeOpaqueWithColor(
                this,
                new com.google.ar.sceneform.rendering.Color(1.0f, 0.05f, 0.02f, 1.0f)
        ).thenAccept(material -> {
            sectionLineRenderable = ShapeFactory.makeCylinder(
                    0.0065f,
                    1.0f,
                    new Vector3(0.0f, 0.0f, 0.0f),
                    material
            );
            sectionPointRenderable = ShapeFactory.makeSphere(
                    0.012f,
                    new Vector3(0.0f, 0.0f, 0.0f),
                    material
            );
        }).exceptionally(throwable -> {
            toast("Could not create cross-section lines: " + throwable.getMessage());
            return null;
        });

        MaterialFactory.makeTransparentWithColor(
                this,
                new com.google.ar.sceneform.rendering.Color(1.0f, 0.08f, 0.02f, 0.22f)
        ).thenAccept(material -> {
            sectionSurfaceFillRenderable = ShapeFactory.makeCylinder(
                    0.0035f,
                    1.0f,
                    new Vector3(0.0f, 0.0f, 0.0f),
                    material
            );
        }).exceptionally(throwable -> {
            toast("Could not create cross-section surface fill: " + throwable.getMessage());
            return null;
        });

        MaterialFactory.makeTransparentWithColor(
                this,
                new com.google.ar.sceneform.rendering.Color(0.70f, 0.70f, 0.70f, 0.22f)
        ).thenAccept(material -> {
            splitSurfaceGuideRenderable = ShapeFactory.makeCylinder(
                    0.0040f,
                    1.0f,
                    new Vector3(0.0f, 0.0f, 0.0f),
                    material
            );
        }).exceptionally(throwable -> {
            toast("Could not create split-surface guide lines: " + throwable.getMessage());
            return null;
        });
    }

    private void handleCubeDragRotation(MotionEvent motionEvent) {
        switch (motionEvent.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                isDraggingCube = true;
                lastTouchX = motionEvent.getX();
                lastTouchY = motionEvent.getY();
                statusText.setText("Drag to rotate the cube. Use SCALE to resize. Press RESET to replace it.");
                break;

            case MotionEvent.ACTION_MOVE:
                if (!isDraggingCube) {
                    isDraggingCube = true;
                    lastTouchX = motionEvent.getX();
                    lastTouchY = motionEvent.getY();
                    break;
                }

                float dx = motionEvent.getX() - lastTouchX;
                float dy = motionEvent.getY() - lastTouchY;

                applyViewRelativeDragRotation(dx, dy);

                lastTouchX = motionEvent.getX();
                lastTouchY = motionEvent.getY();
                break;

            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                isDraggingCube = false;
                break;

            default:
                break;
        }
    }

    private void handleTap(MotionEvent motionEvent) {
        if (edgeLineRenderable == null || sectionLineRenderable == null) {
            toast("AR cube is still loading.");
            return;
        }

        Frame frame = arSceneView.getArFrame();
        if (frame == null) {
            toast("AR frame is not ready yet.");
            return;
        }

        Camera camera = frame.getCamera();
        if (camera.getTrackingState() != TrackingState.TRACKING) {
            toast("Move the phone slowly until tracking starts.");
            return;
        }

        for (HitResult hit : frame.hitTest(motionEvent)) {
            Trackable trackable = hit.getTrackable();
            if (trackable instanceof Plane) {
                Plane plane = (Plane) trackable;
                boolean validPlaneHit = plane.getTrackingState() == TrackingState.TRACKING
                        && plane.isPoseInPolygon(hit.getHitPose())
                        && plane.getType() != Plane.Type.VERTICAL;

                if (validPlaneHit) {
                    placeObject(hit.createAnchor());
                    return;
                }
            }
        }

        toast("No table/surface hit. Move the phone more, then tap the detected surface.");
    }

    private void placeObject(Anchor anchor) {
        resetObject();

        currentAnchor = anchor;
        anchorNode = new AnchorNode(currentAnchor);
        anchorNode.setParent(arSceneView.getScene());

        cubeNode = new Node();
        cubeNode.setParent(anchorNode);

        rotationNode = new Node();
        rotationNode.setParent(cubeNode);
        rotationNode.setLocalPosition(new Vector3(0.0f, HALF_SIDE, 0.0f));
        setRotationNodeIdentity();

        rebuildCubeVisuals();
        applyObjectScale();

        objectPlaced = true;
        setPlaneRendererVisible(false);
        statusText.setText(splitMode
                ? "Cube placed and split. Drag to rotate, use SCALE to resize."
                : "Cube placed. Drag on the screen to rotate it. Use SCALE to resize. Press RESET to replace it.");
    }


    private void updateSplitButtonText() {
        if (splitButton != null) {
            splitButton.setText(splitMode ? "UNSPLIT" : "SPLIT");
        }
    }

    private void toggleSplitMode() {
        if (!splitMode && !isValidSectionForSplit()) {
            toast("Invalid split: use 3 to 6 unique coplanar dots, at most one per cube edge.");
            return;
        }
        splitMode = !splitMode;
        updateSplitButtonText();
        if (objectPlaced && rotationNode != null) {
            rebuildCubeVisuals();
            statusText.setText(splitMode
                    ? "Cube split. Drag to rotate, use SCALE to resize, tap Unsplit to restore."
                    : "Cube restored. Drag to rotate. Use SCALE to resize. Press RESET to replace it.");
        }
    }

    private void clearVisualNodes() {
        for (Node node : visualNodes) {
            try {
                node.setParent(null);
            } catch (Exception ignored) { }
        }
        visualNodes.clear();
    }

    private void rebuildCubeVisuals() {
        if (rotationNode == null) {
            return;
        }
        clearVisualNodes();
        if (splitMode && isValidSectionForSplit()) {
            addSplitCube(rotationNode);
        } else {
            addCubeEdges(rotationNode);
            addCrossSection(rotationNode);
        }
    }

    private String pointLetter(int index) {
        if (index >= 0 && index < 26) {
            return String.valueOf((char) ('A' + index));
        }
        return String.valueOf(index + 1);
    }

    private void addPointLabelNode(Node parent, Vector3 position, String labelText) {
        if (parent == null || labelText == null) {
            return;
        }

        TextView labelView = new TextView(this);
        labelView.setText(labelText);
        labelView.setTextColor(Color.YELLOW);
        labelView.setTextSize(8.0f);
        labelView.setGravity(Gravity.CENTER);
        labelView.setShadowLayer(3.0f, 1.0f, 1.0f, Color.BLACK);
        labelView.setBackgroundColor(Color.TRANSPARENT);
        labelView.setPadding(dp(2), dp(1), dp(2), dp(1));

        ViewRenderable.builder()
                .setView(this, labelView)
                .build()
                .thenAccept(renderable -> {
                    Node labelNode = new Node();
                    labelNode.setParent(parent);
                    labelNode.setRenderable(renderable);
                    labelNode.setLocalPosition(new Vector3(position.x, position.y + 0.018f, position.z));
                    labelNode.setLocalScale(new Vector3(0.18f, 0.18f, 0.18f));
                    visualNodes.add(labelNode);
                })
                .exceptionally(throwable -> null);
    }

    private void addCubeEdges(Node parent) {
        for (int[] edge : CUBE_EDGES) {
            Vector3 a = cubeVertexToLocalPoint(edge[0]);
            Vector3 b = cubeVertexToLocalPoint(edge[1]);
            addLineNode(parent, a, b, edgeLineRenderable);
        }
    }

    private void addCrossSection(Node parent) {
        if (crossSectionPoints.isEmpty()) {
            return;
        }

        ArrayList<Vector3> sorted = sortCrossSectionPoints(crossSectionPoints);

        if (sorted.size() >= 3) {
            addCrossSectionSurface(parent, sorted);
        }

        addSectionPointNodes(parent, sorted);

        if (sorted.size() == 1) {
            return;
        }

        if (sorted.size() == 2) {
            addLineNode(parent, sorted.get(0), sorted.get(1), sectionLineRenderable);
            return;
        }

        addPolygonLineLoop(parent, sorted, sectionLineRenderable);
    }

    private void addCrossSectionSurface(Node parent, ArrayList<Vector3> sorted) {
        if (sectionSurfaceFillRenderable == null || sorted.size() < 3) {
            return;
        }

        Vector3 center = centroid(sorted);
        for (Vector3 p : sorted) {
            addLineNode(parent, center, p, sectionSurfaceFillRenderable);
        }

        for (int i = 0; i < sorted.size(); i++) {
            Vector3 a = sorted.get(i);
            Vector3 b = sorted.get((i + 2) % sorted.size());
            addLineNode(parent, a, b, sectionSurfaceFillRenderable);
        }
    }


    private boolean isValidSectionForSplit() {
        if (crossSectionPoints.size() < 3 || crossSectionPoints.size() > 6) {
            return false;
        }
        ArrayList<Vector3> sorted = sortCrossSectionPoints(crossSectionPoints);
        Vector3 center = centroid(sorted);
        Vector3 normal = estimateSectionNormal(sorted);
        if (vectorLength(normal) < 0.0001f) {
            return false;
        }
        for (Vector3 p : sorted) {
            Vector3 diff = subtract(p, center);
            if (Math.abs(dot(diff, normal)) > 0.012f) {
                return false;
            }
        }
        return true;
    }

    private void addSplitCube(Node parent) {
        ArrayList<Vector3> sorted = sortCrossSectionPoints(crossSectionPoints);
        Vector3 center = centroid(sorted);
        Vector3 normal = normalizeSafe(estimateSectionNormal(sorted));
        if (vectorLength(normal) < 0.0001f) {
            addCubeEdges(parent);
            addCrossSection(parent);
            return;
        }

        addSplitPartEdges(parent, center, normal, 1.0f);
        addSplitPartEdges(parent, center, normal, -1.0f);

        addCrossSectionAtPoints(parent, computeCutPolygonAtOffset(center, normal, 1.0f));
        addCrossSectionAtPoints(parent, computeCutPolygonAtOffset(center, normal, -1.0f));
    }

    private ArrayList<Vector3> computeCutPolygonAtOffset(Vector3 center, Vector3 normal, float side) {
        final float eps = 0.00001f;
        ArrayList<Vector3> points = new ArrayList<>();

        for (int[] edge : CUBE_EDGES) {
            Vector3 a = cubeVertexToLocalPoint(edge[0]);
            Vector3 b = cubeVertexToLocalPoint(edge[1]);
            float da = dot(subtract(a, center), normal);
            float db = dot(subtract(b, center), normal);

            if (Math.abs(da) <= eps) {
                addUniqueVector(points, offsetPoint(a, normal, side));
            }
            if (Math.abs(db) <= eps) {
                addUniqueVector(points, offsetPoint(b, normal, side));
            }
            if (da * db < -eps) {
                float t = da / (da - db);
                Vector3 cut = lerp(a, b, t);
                addUniqueVector(points, offsetPoint(cut, normal, side));
            }
        }

        if (points.size() >= 3) {
            return sortCrossSectionPoints(points);
        }
        return points;
    }

    private boolean addUniqueVector(ArrayList<Vector3> points, Vector3 candidate) {
        for (Vector3 old : points) {
            if (distanceSquared(old, candidate) < UNIQUE_POINT_DISTANCE_SQ) {
                return false;
            }
        }
        points.add(candidate);
        return true;
    }

    private void addSplitPartEdges(Node parent, Vector3 center, Vector3 normal, float side) {
        final float eps = 0.00001f;
        for (int[] edge : CUBE_EDGES) {
            Vector3 a = cubeVertexToLocalPoint(edge[0]);
            Vector3 b = cubeVertexToLocalPoint(edge[1]);
            float da = dot(subtract(a, center), normal);
            float db = dot(subtract(b, center), normal);

            boolean aOnSide = side > 0.0f ? da >= -eps : da <= eps;
            boolean bOnSide = side > 0.0f ? db >= -eps : db <= eps;

            if (aOnSide && bOnSide) {
                addLineNode(parent, offsetPoint(a, normal, side), offsetPoint(b, normal, side), edgeLineRenderable);
            } else if (da * db < -eps) {
                float t = da / (da - db);
                Vector3 cut = lerp(a, b, t);
                if (aOnSide) {
                    addLineNode(parent, offsetPoint(a, normal, side), offsetPoint(cut, normal, side), edgeLineRenderable);
                } else if (bOnSide) {
                    addLineNode(parent, offsetPoint(b, normal, side), offsetPoint(cut, normal, side), edgeLineRenderable);
                }
            }
        }
    }

    private void addSplitSurfaceGuides(Node parent, ArrayList<Vector3> points) {
        if (splitSurfaceGuideRenderable == null || points.size() < 3) {
            return;
        }

        addPolygonLineLoop(parent, points, splitSurfaceGuideRenderable);
        if (points.size() > 3) {
            Vector3 first = points.get(0);
            for (int i = 2; i < points.size() - 1; i++) {
                addLineNode(parent, first, points.get(i), splitSurfaceGuideRenderable);
            }
        }
    }

    private void addCrossSectionAtPoints(Node parent, ArrayList<Vector3> shifted) {
        addSplitSurfaceGuides(parent, shifted);
        addCrossSectionSurface(parent, shifted);

        addSectionPointNodes(parent, shifted);

        if (shifted.size() >= 2) {
            addPolygonLineLoop(parent, shifted, sectionLineRenderable);
        }
    }

    private void addSectionPointNodes(Node parent, List<Vector3> points) {
        if (sectionPointRenderable == null) {
            return;
        }

        for (int i = 0; i < points.size(); i++) {
            Vector3 p = points.get(i);
            Node pointNode = new Node();
            pointNode.setParent(parent);
            pointNode.setRenderable(sectionPointRenderable);
            pointNode.setLocalPosition(p);
            visualNodes.add(pointNode);
            addPointLabelNode(parent, p, pointLetter(i));
        }
    }

    private void addPolygonLineLoop(Node parent, List<Vector3> points, ModelRenderable renderable) {
        if (points.size() < 2) {
            return;
        }

        for (int i = 0; i < points.size(); i++) {
            Vector3 a = points.get(i);
            Vector3 b = points.get((i + 1) % points.size());
            addLineNode(parent, a, b, renderable);
        }
    }

    private Vector3 offsetPoint(Vector3 p, Vector3 normal, float side) {
        return new Vector3(
                p.x + normal.x * SPLIT_OFFSET_METERS * side,
                p.y + normal.y * SPLIT_OFFSET_METERS * side,
                p.z + normal.z * SPLIT_OFFSET_METERS * side
        );
    }

    private Vector3 subtract(Vector3 a, Vector3 b) {
        return new Vector3(a.x - b.x, a.y - b.y, a.z - b.z);
    }

    private Vector3 lerp(Vector3 a, Vector3 b, float t) {
        return new Vector3(
                a.x + (b.x - a.x) * t,
                a.y + (b.y - a.y) * t,
                a.z + (b.z - a.z) * t
        );
    }

    private void addLineNode(Node parent, Vector3 a, Vector3 b, ModelRenderable renderable) {
        if (renderable == null) {
            return;
        }

        Vector3 delta = subtract(b, a);
        float length = vectorLength(delta);
        if (length < MIN_LINE_LENGTH) {
            return;
        }

        Vector3 midpoint = new Vector3(
                0.5f * (a.x + b.x),
                0.5f * (a.y + b.y),
                0.5f * (a.z + b.z)
        );
        Vector3 direction = new Vector3(delta.x / length, delta.y / length, delta.z / length);

        Node lineNode = new Node();
        lineNode.setParent(parent);
        lineNode.setRenderable(renderable);
        lineNode.setLocalPosition(midpoint);
        lineNode.setLocalRotation(Quaternion.rotationBetweenVectors(new Vector3(0.0f, 1.0f, 0.0f), direction));
        lineNode.setLocalScale(new Vector3(1.0f, length, 1.0f));
        visualNodes.add(lineNode);
    }

    private void loadCubePayloadFromIntent() {
        crossSectionPoints.clear();

        try {
            String payload = getIntent().getStringExtra("cube_payload_json");
            if (payload == null || payload.trim().isEmpty()) {
                return;
            }

            JSONObject root = new JSONObject(payload);
            splitMode = root.optBoolean("split_requested", false);
            updateSplitButtonText();

            JSONArray intersections = root.optJSONArray("intersections");
            if (intersections == null) {
                return;
            }

            for (int i = 0; i < intersections.length(); i++) {
                JSONObject item = intersections.optJSONObject(i);
                if (item == null) {
                    continue;
                }

                int v0 = item.optInt("v0", -1);
                int v1 = item.optInt("v1", -1);
                double tRaw = item.optDouble("t", Double.NaN);

                if (v0 < 0 || v0 >= CUBE_VERTICES.length || v1 < 0 || v1 >= CUBE_VERTICES.length || Double.isNaN(tRaw)) {
                    continue;
                }

                if (crossSectionPoints.size() >= 6) {
                    continue;
                }
                float t = clamp01((float) tRaw);
                Vector3 point = pointOnCubeEdge(v0, v1, t);
                addUniqueVector(crossSectionPoints, point);
            }

            if (splitMode && !isValidSectionForSplit()) {
                splitMode = false;
                updateSplitButtonText();
            }
        } catch (Exception ignored) { }
    }

    private Vector3 pointOnCubeEdge(int v0, int v1, float t) {
        Vector3 a = cubeVertexToLocalPoint(v0);
        Vector3 b = cubeVertexToLocalPoint(v1);
        return new Vector3(
                (1.0f - t) * a.x + t * b.x,
                (1.0f - t) * a.y + t * b.y,
                (1.0f - t) * a.z + t * b.z
        );
    }

    private Vector3 cubeVertexToLocalPoint(int index) {
        float[] v = CUBE_VERTICES[index];
        return new Vector3(
                v[0] * HALF_SIDE,
                v[1] * HALF_SIDE,
                v[2] * HALF_SIDE
        );
    }

    private ArrayList<Vector3> sortCrossSectionPoints(List<Vector3> points) {
        ArrayList<Vector3> sorted = new ArrayList<>(points);
        if (sorted.size() <= 2) {
            return sorted;
        }

        Vector3 center = centroid(sorted);
        Vector3 normal = estimateSectionNormal(sorted);
        Vector3 u = normalizeSafe(new Vector3(sorted.get(0).x - center.x, sorted.get(0).y - center.y, sorted.get(0).z - center.z));
        if (vectorLength(u) < 0.0001f) {
            u = new Vector3(1.0f, 0.0f, 0.0f);
        }
        Vector3 v = normalizeSafe(cross(normal, u));

        final Vector3 c = center;
        final Vector3 basisU = u;
        final Vector3 basisV = v;

        sorted.sort((p1, p2) -> {
            Vector3 d1 = subtract(p1, c);
            Vector3 d2 = subtract(p2, c);
            double a1 = Math.atan2(dot(d1, basisV), dot(d1, basisU));
            double a2 = Math.atan2(dot(d2, basisV), dot(d2, basisU));
            return Double.compare(a1, a2);
        });

        return sorted;
    }

    private Vector3 centroid(List<Vector3> points) {
        float x = 0.0f;
        float y = 0.0f;
        float z = 0.0f;
        for (Vector3 p : points) {
            x += p.x;
            y += p.y;
            z += p.z;
        }
        float inv = 1.0f / Math.max(points.size(), 1);
        return new Vector3(x * inv, y * inv, z * inv);
    }

    private Vector3 estimateSectionNormal(List<Vector3> points) {
        Vector3 center = centroid(points);
        for (int i = 0; i < points.size(); i++) {
            Vector3 a = new Vector3(points.get(i).x - center.x, points.get(i).y - center.y, points.get(i).z - center.z);
            for (int j = i + 1; j < points.size(); j++) {
                Vector3 b = new Vector3(points.get(j).x - center.x, points.get(j).y - center.y, points.get(j).z - center.z);
                Vector3 n = cross(a, b);
                if (vectorLength(n) > 0.0001f) {
                    return normalizeSafe(n);
                }
            }
        }
        return new Vector3(0.0f, 1.0f, 0.0f);
    }

    private Vector3 cross(Vector3 a, Vector3 b) {
        return new Vector3(
                a.y * b.z - a.z * b.y,
                a.z * b.x - a.x * b.z,
                a.x * b.y - a.y * b.x
        );
    }

    private float dot(Vector3 a, Vector3 b) {
        return a.x * b.x + a.y * b.y + a.z * b.z;
    }

    private Vector3 normalizeSafe(Vector3 value) {
        float length = vectorLength(value);
        if (length < 0.000001f) {
            return new Vector3(0.0f, 0.0f, 0.0f);
        }
        return new Vector3(value.x / length, value.y / length, value.z / length);
    }

    private float vectorLength(Vector3 value) {
        return (float) Math.sqrt(value.x * value.x + value.y * value.y + value.z * value.z);
    }

    private float distanceSquared(Vector3 a, Vector3 b) {
        float dx = a.x - b.x;
        float dy = a.y - b.y;
        float dz = a.z - b.z;
        return dx * dx + dy * dy + dz * dz;
    }

    private float clamp01(float value) {
        return Math.max(0.0f, Math.min(1.0f, value));
    }

    private void resetObject() {
        objectPlaced = false;

        clearVisualNodes();

        if (rotationNode != null) {
            rotationNode.setParent(null);
            rotationNode = null;
        }

        if (cubeNode != null) {
            cubeNode.setParent(null);
            cubeNode = null;
        }

        isDraggingCube = false;
        if (anchorNode != null) {
            anchorNode.setParent(null);
            anchorNode = null;
        }

        if (currentAnchor != null) {
            currentAnchor.detach();
            currentAnchor = null;
        }

        updateSplitButtonText();
        setPlaneRendererVisible(true);

        if (statusText != null) {
            statusText.setText(STATUS_SCANNING);
        }
    }

    private void applyViewRelativeDragRotation(float dx, float dy) {
        if (rotationNode == null) {
            return;
        }

        Frame frame = arSceneView.getArFrame();
        if (frame == null) {
            return;
        }

        Camera camera = frame.getCamera();
        if (camera.getTrackingState() != TrackingState.TRACKING) {
            return;
        }

        try {
            float[] rightRaw = camera.getPose().getXAxis();
            float[] upRaw = camera.getPose().getYAxis();

            Vector3 cameraRight = normalizeSafe(new Vector3(rightRaw[0], rightRaw[1], rightRaw[2]));
            Vector3 cameraUp = normalizeSafe(new Vector3(upRaw[0], upRaw[1], upRaw[2]));

            Quaternion currentWorldRotation = (Quaternion) rotationNode.getClass()
                    .getMethod("getWorldRotation")
                    .invoke(rotationNode);

            Quaternion rotateHorizontal = makeAxisAngle(cameraUp, dy * ROTATION_SENSITIVITY);
            Quaternion rotateVertical = makeAxisAngle(cameraRight, -dx * ROTATION_SENSITIVITY);

            Quaternion combined = multiplyQuaternions(rotateHorizontal, currentWorldRotation);
            combined = multiplyQuaternions(rotateVertical, combined);

            rotationNode.getClass()
                    .getMethod("setWorldRotation", Quaternion.class)
                    .invoke(rotationNode, combined);
        } catch (Exception ignored) { }
    }

    private void setRotationNodeIdentity() {
        if (rotationNode == null) {
            return;
        }
        try {
            rotationNode.setLocalRotation(makeAxisAngle(new Vector3(0.0f, 1.0f, 0.0f), 0.0f));
        } catch (Exception ignored) { }
    }

    private Quaternion makeAxisAngle(Vector3 axis, float degrees) throws Exception {
        Method axisAngle = Quaternion.class.getMethod("axisAngle", Vector3.class, float.class);
        return (Quaternion) axisAngle.invoke(null, axis, degrees);
    }

    private Quaternion multiplyQuaternions(Quaternion first, Quaternion second) throws Exception {
        Method multiply = Quaternion.class.getMethod("multiply", Quaternion.class, Quaternion.class);
        return (Quaternion) multiply.invoke(null, first, second);
    }

    private void applyObjectScale() {
        if (cubeNode != null) {
            float displayedScale = AR_BASE_SCALE * objectScale;
            cubeNode.setLocalScale(new Vector3(displayedScale, displayedScale, displayedScale));
        }
    }

    private void updateStatusFromTracking() {
        if (objectPlaced) {
            return;
        }

        Frame frame = arSceneView.getArFrame();
        if (frame == null) {
            return;
        }

        Camera camera = frame.getCamera();
        if (camera.getTrackingState() != TrackingState.TRACKING) {
            statusText.setText(STATUS_SCANNING);
            return;
        }

        if (hasTrackingHorizontalPlane()) {
            statusText.setText("Surface found. Tap the table/floor where the cube should appear.");
        } else {
            statusText.setText(STATUS_SCANNING);
        }
    }

    private boolean hasTrackingHorizontalPlane() {
        if (arSession == null) {
            return false;
        }

        Collection<Plane> planes = arSession.getAllTrackables(Plane.class);
        for (Plane plane : planes) {
            if (plane.getTrackingState() == TrackingState.TRACKING && plane.getType() != Plane.Type.VERTICAL) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (!hasCameraPermission()) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_CODE);
            return;
        }

        if (arSession == null) {
            try {
                ArCoreApk.InstallStatus installStatus = ArCoreApk.getInstance().requestInstall(this, !installRequested);
                if (installStatus == ArCoreApk.InstallStatus.INSTALL_REQUESTED) {
                    installRequested = true;
                    return;
                }

                arSession = new Session(this);
                Config config = new Config(arSession);
                config.setPlaneFindingMode(Config.PlaneFindingMode.HORIZONTAL);
                config.setUpdateMode(Config.UpdateMode.LATEST_CAMERA_IMAGE);

                try {
                    config.setLightEstimationMode(Config.LightEstimationMode.DISABLED);
                } catch (Exception ignored) { }

                arSession.configure(config);
                setupArSceneViewSession();
                configurePlaneRenderer();
            } catch (UnavailableArcoreNotInstalledException e) {
                showFatalError("ARCore is not installed.");
                return;
            } catch (UnavailableUserDeclinedInstallationException e) {
                showFatalError("ARCore installation was declined.");
                return;
            } catch (UnavailableApkTooOldException e) {
                showFatalError("Google Play Services for AR is too old. Update it and try again.");
                return;
            } catch (UnavailableSdkTooOldException e) {
                showFatalError("This ARCore SDK is too old for the installed AR service.");
                return;
            } catch (UnavailableDeviceNotCompatibleException e) {
                showFatalError("This device is not compatible with ARCore.");
                return;
            } catch (Exception e) {
                showFatalError("Could not start ARCore: " + e.getMessage());
                return;
            }
        }

        try {
            arSceneView.resume();
        } catch (CameraNotAvailableException e) {
            showFatalError("Camera is not available. Close other camera apps and try again.");
        } catch (Exception e) {
            showFatalError("Could not resume AR scene: " + e.getMessage());
        }
    }

    private void setupArSceneViewSession() throws Exception {
        try {
            Method setSession = arSceneView.getClass().getMethod("setSession", Session.class);
            setSession.invoke(arSceneView, arSession);
            return;
        } catch (NoSuchMethodException ignored) { }

        try {
            Method setupSession = arSceneView.getClass().getMethod("setupSession", Session.class);
            setupSession.invoke(arSceneView, arSession);
            return;
        } catch (NoSuchMethodException ignored) { }

        throw new NoSuchMethodException(
                "This Sceneform ArSceneView has neither setSession(Session) nor setupSession(Session)."
        );
    }

    private void configurePlaneRenderer() {
        setPlaneRendererVisible(true);
        try {
            Object planeRenderer = arSceneView.getClass().getMethod("getPlaneRenderer").invoke(arSceneView);
            try {
                planeRenderer.getClass().getMethod("setShadowReceiver", boolean.class).invoke(planeRenderer, false);
            } catch (Exception ignored) { }
        } catch (Exception ignored) { }
    }

    private void setPlaneRendererVisible(boolean visible) {
        try {
            Object planeRenderer = arSceneView.getClass().getMethod("getPlaneRenderer").invoke(arSceneView);
            planeRenderer.getClass().getMethod("setVisible", boolean.class).invoke(planeRenderer, visible);
        } catch (Exception ignored) { }
    }

    @Override
    protected void onPause() {
        if (arSceneView != null) {
            arSceneView.pause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        resetObject();
        if (arSceneView != null) {
            arSceneView.destroy();
        }
        if (arSession != null) {
            arSession.close();
            arSession = null;
        }
        super.onDestroy();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                onResume();
            } else {
                showFatalError("Camera permission is required for AR mode.");
            }
        }
    }

    private boolean hasCameraPermission() {
        return checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    private void showFatalError(String message) {
        toast(message);
        if (statusText != null) {
            statusText.setText(message);
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
