import { Route, Switch } from "wouter";
import { CmsBuilder } from "./CmsBuilder";
import {
  AuditLog,
  CmsDashboard,
  ContentLibrary,
  FeatureFlags,
  JobControl,
  MediaLibrary,
  ReviewQueue,
} from "./CmsOperations";
import { ContentWorkspace } from "./CmsWorkflow";
import {
  DraftLabWorkspace,
  DraftMissionWorkspace,
} from "./CmsPreviewWorkspaces";

export function CmsApp() {
  return (
    <main className="competition-shell portal-shell">
      <Switch>
        <Route
          path="/cms/preview/lab/:contentId/:versionId"
          component={DraftLabWorkspace}
        />
        <Route
          path="/cms/preview/mission/:contentId/:versionId"
          component={DraftMissionWorkspace}
        />
        <Route path="/cms/library" component={ContentLibrary} />
        <Route path="/cms/builders/:type/:contentId" component={CmsBuilder} />
        <Route path="/cms/builders/:type" component={CmsBuilder} />
        <Route path="/cms/content/:contentId" component={ContentWorkspace} />
        <Route path="/cms/reviews" component={ReviewQueue} />
        <Route path="/cms/media" component={MediaLibrary} />
        <Route path="/cms/flags" component={FeatureFlags} />
        <Route path="/cms/audit" component={AuditLog} />
        <Route path="/cms/jobs" component={JobControl} />
        <Route path="/cms" component={CmsDashboard} />
      </Switch>
    </main>
  );
}
