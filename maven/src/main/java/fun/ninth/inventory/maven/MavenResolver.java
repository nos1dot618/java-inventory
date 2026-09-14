package fun.ninth.inventory.maven;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.apache.maven.model.DependencyManagement;
import org.apache.maven.model.Model;
import org.apache.maven.model.Profile;
import org.apache.maven.model.building.DefaultModelBuilderFactory;
import org.apache.maven.model.building.DefaultModelBuildingRequest;
import org.apache.maven.model.building.ModelBuildingRequest;
import org.apache.maven.model.building.ModelBuildingResult;
import org.apache.maven.model.building.ModelBuildingException;
import org.eclipse.aether.RepositorySystem;
import org.eclipse.aether.DefaultRepositorySystemSession;
import org.eclipse.aether.artifact.DefaultArtifact;
import org.eclipse.aether.collection.CollectRequest;
import org.eclipse.aether.collection.DependencyCollectionException;
import org.eclipse.aether.graph.Dependency;
import org.eclipse.aether.graph.DependencyNode;
import org.eclipse.aether.repository.LocalRepository;
import org.eclipse.aether.repository.RemoteRepository;
import org.apache.maven.repository.internal.MavenRepositorySystemUtils;
import org.eclipse.aether.impl.DefaultServiceLocator;
import org.eclipse.aether.spi.connector.RepositoryConnectorFactory;
import org.eclipse.aether.connector.basic.BasicRepositoryConnectorFactory;
import org.eclipse.aether.spi.connector.transport.TransporterFactory;
import org.eclipse.aether.transport.http.HttpTransporterFactory;

import java.io.File;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class MavenResolver {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private MavenResolver() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: java -jar maven-resolver.jar <project-dir>");
            System.exit(2);
        }

        Path projectDir = Path.of(args[0]).toAbsolutePath().normalize();
        Path pom = projectDir.resolve("pom.xml");
        if (!pom.toFile().isFile()) {
            throw new IllegalArgumentException("Maven POM not found: " + pom);
        }

        Result result = new Resolver().resolve(projectDir, pom.toFile());
        System.out.println(GSON.toJson(result));
    }

    private static final class Resolver {
        private final RepositorySystem system;
        private final DefaultRepositorySystemSession session;
        private final List<RemoteRepository> repositories;
        private final DefaultModelBuilderFactory modelBuilderFactory = new DefaultModelBuilderFactory();

        Resolver() {
            DefaultServiceLocator locator = MavenRepositorySystemUtils.newServiceLocator();
            locator.addService(RepositoryConnectorFactory.class, BasicRepositoryConnectorFactory.class);
            locator.addService(TransporterFactory.class, HttpTransporterFactory.class);
            system = locator.getService(RepositorySystem.class);
            if (system == null) {
                throw new IllegalStateException("failed to initialize Maven RepositorySystem");
            }
            session = MavenRepositorySystemUtils.newSession();
            LocalRepository localRepository = new LocalRepository(
                    Path.of(System.getProperty("user.home"), ".m2", "repository").toFile());
            session.setLocalRepositoryManager(system.newLocalRepositoryManager(session, localRepository));
            repositories = List.of(
                    new RemoteRepository.Builder(
                            "central", "default", "https://repo.maven.apache.org/maven2").build());
        }

        Result resolve(Path projectDir, File pom) throws ModelBuildingException, DependencyCollectionException {
            ModelBuildingResult modelResult = buildModel(pom);
            Model effective = modelResult.getEffectiveModel();
            Model raw = modelResult.getRawModel();

            List<Module> modules = new ArrayList<>();
            modules.add(resolveModule(projectDir, pom, effective, raw));
            for (String modulePath : effective.getModules()) {
                Path childPom = pom.toPath().getParent().resolve(modulePath).resolve("pom.xml").normalize();
                if (!childPom.toFile().isFile()) {
                    continue;
                }
                ModelBuildingResult child = buildModel(childPom.toFile());
                modules.add(
                        resolveModule(projectDir, childPom.toFile(), child.getEffectiveModel(), child.getRawModel()));
            }

            return new Result(new Project(effective.getGroupId(), effective.getArtifactId(), effective.getVersion()),
                    modules);
        }

        private ModelBuildingResult buildModel(File pom) throws ModelBuildingException {
            DefaultModelBuildingRequest request = new DefaultModelBuildingRequest();
            request.setPomFile(pom);
            request.setProcessPlugins(false);
            request.setValidationLevel(ModelBuildingRequest.VALIDATION_LEVEL_MINIMAL);
            request.setSystemProperties(System.getProperties());
            return modelBuilderFactory.newInstance().build(request);
        }

        private Module resolveModule(Path projectDir, File pom, Model effective, Model raw)
                throws DependencyCollectionException {
            Set<String> direct = new HashSet<>();
            Map<String, String> declaredVersions = new HashMap<>();
            for (org.apache.maven.model.Dependency dependency : raw.getDependencies()) {
                String key = dependency.getGroupId() + ":" + dependency.getArtifactId();
                direct.add(key);
                declaredVersions.put(key, dependency.getVersion());
            }

            List<Dependency> roots = new ArrayList<>();
            for (org.apache.maven.model.Dependency dependency : effective.getDependencies()) {
                if (dependency.getVersion() == null || dependency.getVersion().isBlank()) {
                    continue;
                }
                String classifier = dependency.getClassifier() == null ? "" : dependency.getClassifier();
                String extension = dependency.getType() == null ? "jar" : dependency.getType();
                DefaultArtifact artifact = new DefaultArtifact(
                        dependency.getGroupId(), dependency.getArtifactId(), classifier, extension,
                        dependency.getVersion());
                roots.add(new Dependency(artifact, dependency.getScope(), dependency.isOptional()));
            }

            CollectRequest request = new CollectRequest();
            request.setDependencies(roots);
            request.setRepositories(repositories);
            DependencyNode root = system.collectDependencies(session, request).getRoot();

            List<DependencyRecord> records = new ArrayList<>();
            root.accept(new org.eclipse.aether.graph.DependencyVisitor() {
                @Override
                public boolean visitEnter(DependencyNode node) {
                    if (node.getDependency() == null || node.getArtifact() == null) {
                        return true;
                    }
                    String key = node.getArtifact().getGroupId() + ":" + node.getArtifact().getArtifactId();
                    records.add(new DependencyRecord(
                            node.getArtifact().getGroupId(),
                            node.getArtifact().getArtifactId(),
                            declaredVersions.get(key),
                            node.getArtifact().getVersion(),
                            node.getDependency().getScope(),
                            direct.contains(key),
                            node.getDependency().isOptional()));
                    return true;
                }

                @Override
                public boolean visitLeave(DependencyNode node) {
                    return true;
                }
            });

            String relative = projectDir.relativize(pom.toPath().getParent()).toString();
            if (relative.isEmpty())
                relative = ".";
            return new Module(effective.getGroupId(), effective.getArtifactId(), effective.getVersion(), relative,
                    records);
        }
    }

    private record Result(Project project, List<Module> modules) {
    }

    private record Project(String groupId, String artifactId, String version) {
    }

    private record Module(String groupId, String artifactId, String version, String path,
            List<DependencyRecord> dependencies) {
    }

    private record DependencyRecord(String groupId, String artifactId, String declaredVersion,
            String resolvedVersion, String scope, boolean direct, boolean optional) {
    }
}
