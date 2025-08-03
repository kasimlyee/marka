import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  Users,
  FileText,
  Settings,
  BarChart3,
  Upload,
  Download,
  Plus,
  Search,
  Filter,
  Edit,
  Trash2,
  Save,
  X,
  CheckCircle,
  AlertCircle,
  Menu,
  User,
  GraduationCap,
  Key,
  Shield,
  Database,
  Printer,
  Eye,
  Calendar,
  Award,
  TrendingUp,
  FileCheck,
  Copy,
  RefreshCw,
  Lock,
  Unlock,
  Cloud,
  HardDrive,
  UserPlus,
  BookPlus,
  Loader2,
} from "lucide-react";

const MarkaApp = () => {
  // State management
  const [currentView, setCurrentView] = useState("dashboard");
  const [students, setStudents] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterClass, setFilterClass] = useState("All");
  const [notification, setNotification] = useState(null);
  const [currentTerm, setCurrentTerm] = useState("term1");
  const [gradingSchemas, setGradingSchemas] = useState({});
  const [activeSchema, setActiveSchema] = useState("PLE");
  const [licenseInfo, setLicenseInfo] = useState({});
  const [schoolData, setSchoolData] = useState({});
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [systemInfo, setSystemInfo] = useState({});
  const [performanceMetrics, setPerformanceMetrics] = useState({});
  const [settings, setSettings] = useState({});

  // Theme colors
  const theme = {
    primary: "#1D3557",
    secondary: "#2A9D8F",
    accent: "#F4A261",
    background: "#F1FAEE",
    error: "#E63946",
    success: "#10B981",
    warning: "#F59E0B",
  };

  // Initialize data from Electron backend
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);

        if (!window.electronAPI) {
          throw new Error(
            "Electron API is not available. Ensure the app is running in Electron."
          );
        }

        // Load initial data from Electron backend
        //@ts-ignore
        const [
          studentsData,
          subjectsData,
          licenseData,
          schoolData,
          usersData,
          systemData,
          performanceData,
          settingsData,
        ] = await Promise.all([
          window.electronAPI.students.getAll().catch(() => []),
          window.electronAPI.subjects.getAll().catch(() => []),
          window.electronAPI.license.getInfo().catch(() => {}),
          window.electronAPI.settings.getAll().catch(() => {}),
          window.electronAPI.settings.get("schoolData") || {},
          window.electronAPI.system.getInfo().catch(() => {}),
          window.electronAPI.system.getPerformance().catch(() => {}),
          window.electronAPI.settings.getAll().catch,
        ]);

        setStudents(studentsData);
        setSubjects(subjectsData);
        setLicenseInfo(licenseData);
        setSchoolData(schoolData);
        setUsers(usersData);
        setSystemInfo(systemData);
        setPerformanceMetrics(performanceData);
        setSettings(settingsData);

        // Set up listeners for menu actions
        window.electronAPI.onMenuAction((action) => {
          switch (action) {
            case "new-student":
              openModal("addStudent");
              break;
            case "generate-report":
              setCurrentView("reports");
              break;
          }
        });

        // Set up listeners for notifications
        window.electronAPI.onNotification((notification) => {
          showNotification(notification.message, notification.type);
        });

        // Load grading schemas from settings
        const gradingSchemas =
          (await window.electronAPI.settings.get("gradingSchemas")) || {};
        setGradingSchemas(gradingSchemas);
        setActiveSchema(
          (await window.electronAPI.settings.get("activeSchema")) || "PLE"
        );

        setIsLoading(false);
      } catch (error) {
        console.error("Failed to load initial data:", error);
        showNotification("Failed to load application data", "error");
        setIsLoading(false);
      }
    };

    loadData();

    return () => {
      window.electronAPI.removeAllListeners("menu-action");
      window.electronAPI.removeAllListeners("notification");
    };
  }, []);
  console.log("window.electronAPI:", window.electronAPI);
  // Utility functions
  const showNotification = (message, type = "success", duration = 3000) => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), duration);
  };

  const openModal = (type, data = null) => {
    setModalType(type);
    setShowModal(true);
    if (type === "editStudent") setSelectedStudent(data);
    if (type === "editSubject") setSelectedSubject(data);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedStudent(null);
    setSelectedSubject(null);
  };

  const calculateGrade = (subjects, gradingSystem = "PLE") => {
    const schema = gradingSchemas[gradingSystem];
    if (!schema) return { grade: "N/A", color: "#6B7280" };

    const scores = Object.values(subjects).map((termScores) =>
      typeof termScores === "object"
        ? (termScores.term1 + termScores.term2 + termScores.term3) / 3
        : termScores
    );
    const average =
      scores.reduce((sum, score) => sum + score, 0) / scores.length;

    if (schema.type === "division") {
      const aggregate = Math.ceil((100 - average) / 3);
      for (const range of schema.gradeRanges) {
        if (aggregate <= range.maxAggregate) {
          return { grade: range.grade, aggregate, color: range.color };
        }
      }
    } else {
      for (const range of schema.gradeRanges) {
        if (average >= range.minPercent) {
          return { grade: range.grade, color: range.color };
        }
      }
    }

    return { grade: "F", color: "#6B7280" };
  };

  const getClassList = () => {
    const classes = [...new Set(students.map((s) => s.class))];
    return ["All", ...classes.sort()];
  };

  const filteredStudents = students.filter((student) => {
    const matchesSearch =
      student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.studentId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesClass = filterClass === "All" || student.class === filterClass;
    return matchesSearch && matchesClass;
  });

  const generatePDFReport = async (student) => {
    try {
      const result = await window.electronAPI.reports.generatePDF({
        student,
        schoolData,
        gradingSchema: gradingSchemas[activeSchema],
      });

      if (result.success) {
        showNotification(`PDF report generated for ${student.name}`, "success");
      } else {
        showNotification(`Failed to generate report: ${result.error}`, "error");
      }
    } catch (error) {
      showNotification("Failed to generate report", "error");
      console.error("Report generation error:", error);
    }
  };

  const exportStudentData = async () => {
    try {
      const result = await window.electronAPI.files.exportStudents("csv");
      if (result.success) {
        showNotification("Student data exported successfully", "success");
      } else {
        showNotification(`Export failed: ${result.error}`, "error");
      }
    } catch (error) {
      showNotification("Failed to export student data", "error");
      console.error("Export error:", error);
    }
  };

  const handleBackupDatabase = async () => {
    try {
      const result = await window.electronAPI.backup.create();
      if (result.success) {
        showNotification(`Database backup created: ${result.path}`, "success");
      } else {
        showNotification(`Backup failed: ${result.error}`, "error");
      }
    } catch (error) {
      showNotification("Failed to create backup", "error");
      console.error("Backup error:", error);
    }
  };

  const handleRestoreDatabase = async () => {
    try {
      const result = await window.electronAPI.files.selectFolder();
      if (!result.canceled && result.filePaths.length > 0) {
        const confirmed = window.confirm(
          "Are you sure you want to restore from backup? This will replace all current data."
        );
        if (confirmed) {
          const restoreResult = await window.electronAPI.backup.restore(
            result.filePaths[0]
          );
          if (restoreResult.success) {
            showNotification(
              "Database restored successfully. Application will restart.",
              "success"
            );
            setTimeout(() => window.location.reload(), 2000);
          } else {
            showNotification(`Restore failed: ${restoreResult.error}`, "error");
          }
        }
      }
    } catch (error) {
      showNotification("Failed to restore backup", "error");
      console.error("Restore error:", error);
    }
  };

  const handleCloudSync = async () => {
    try {
      const result = await window.electronAPI.sync.toCloud();
      if (result.success) {
        showNotification("Data synchronized to cloud successfully", "success");
      } else {
        showNotification(`Sync failed: ${result.error}`, "error");
      }
    } catch (error) {
      showNotification("Failed to sync to cloud", "error");
      console.error("Cloud sync error:", error);
    }
  };

  const saveStudent = async (studentData) => {
    try {
      let result;
      if (studentData.id) {
        result = await window.electronAPI.students.update(
          studentData.id,
          studentData
        );
      } else {
        result = await window.electronAPI.students.create(studentData);
      }

      if (result) {
        const updatedStudents = await window.electronAPI.students.getAll();
        setStudents(updatedStudents);
        showNotification(
          `Student ${studentData.id ? "updated" : "added"} successfully`,
          "success"
        );
        return true;
      }
    } catch (error) {
      showNotification(
        `Failed to ${studentData.id ? "update" : "add"} student`,
        "error"
      );
      console.error("Student save error:", error);
      return false;
    }
  };

  const deleteStudent = async (studentId) => {
    try {
      const result = await window.electronAPI.students.delete(studentId);
      if (result) {
        const updatedStudents = await window.electronAPI.students.getAll();
        setStudents(updatedStudents);
        showNotification("Student deleted successfully", "success");
        return true;
      }
    } catch (error) {
      showNotification("Failed to delete student", "error");
      console.error("Student delete error:", error);
      return false;
    }
  };

  const saveSubject = async (subjectData) => {
    try {
      let result;
      if (subjectData.id) {
        result = await window.electronAPI.subjects.update(
          subjectData.id,
          subjectData
        );
      } else {
        result = await window.electronAPI.subjects.create(subjectData);
      }

      if (result) {
        const updatedSubjects = await window.electronAPI.subjects.getAll();
        setSubjects(updatedSubjects);
        showNotification(
          `Subject ${subjectData.id ? "updated" : "added"} successfully`,
          "success"
        );
        return true;
      }
    } catch (error) {
      showNotification(
        `Failed to ${subjectData.id ? "update" : "add"} subject`,
        "error"
      );
      console.error("Subject save error:", error);
      return false;
    }
  };

  const deleteSubject = async (subjectId) => {
    try {
      const result = await window.electronAPI.subjects.delete(subjectId);
      if (result) {
        const updatedSubjects = await window.electronAPI.subjects.getAll();
        setSubjects(updatedSubjects);
        showNotification("Subject deleted successfully", "success");
        return true;
      }
    } catch (error) {
      showNotification("Failed to delete subject", "error");
      console.error("Subject delete error:", error);
      return false;
    }
  };

  const saveSettings = async (key, value) => {
    try {
      const result = await window.electronAPI.settings.set(key, value);
      if (result) {
        const updatedSettings = await window.electronAPI.settings.getAll();
        setSettings(updatedSettings);
        showNotification("Settings saved successfully", "success");
        return true;
      }
    } catch (error) {
      showNotification("Failed to save settings", "error");
      console.error("Settings save error:", error);
      return false;
    }
  };

  // Components
  const Sidebar = () => (
    <div
      className="w-64 bg-white shadow-lg h-full flex flex-col"
      style={{ borderRight: `2px solid ${theme.secondary}` }}
    >
      <div className="p-6 border-b" style={{ borderColor: theme.secondary }}>
        <div className="flex items-center space-x-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: theme.secondary }}
          >
            <span className="text-white font-bold text-xl">M</span>
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: theme.primary }}>
              Marka
            </h1>
            <p className="text-sm text-gray-500">Report Card System</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <div className="space-y-2">
          {[
            { id: "dashboard", icon: BarChart3, label: "Dashboard" },
            { id: "students", icon: Users, label: "Students" },
            { id: "subjects", icon: BookOpen, label: "Subjects" },
            { id: "reports", icon: FileText, label: "Reports" },
            {
              id: "analytics",
              icon: TrendingUp,
              label: "Analytics",
              locked: licenseInfo.type === "Standard",
            },
            {
              id: "users",
              icon: UserPlus,
              label: "User Management",
              locked: licenseInfo.type !== "Enterprise",
            },
            { id: "settings", icon: Settings, label: "Settings" },
            { id: "license", icon: Key, label: "License" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() =>
                item.locked
                  ? showNotification(
                      `Feature requires ${
                        item.id === "analytics" ? "Pro" : "Enterprise"
                      } license`,
                      "warning"
                    )
                  : setCurrentView(item.id)
              }
              className={`w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors ${
                currentView === item.id
                  ? "text-white"
                  : item.locked
                  ? "text-gray-400"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
              style={{
                backgroundColor:
                  currentView === item.id ? theme.secondary : "transparent",
              }}
            >
              <div className="flex items-center space-x-3">
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </div>
              {item.locked && <Lock className="w-4 h-4" />}
            </button>
          ))}
        </div>
      </nav>

      <div className="p-4 border-t">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Shield className="w-4 h-4" style={{ color: theme.secondary }} />
            <span
              className="font-semibold text-sm"
              style={{ color: theme.primary }}
            >
              {licenseInfo.type || "Loading..."} License
            </span>
          </div>
          <p className="text-xs text-gray-600">
            Expires: {licenseInfo.expiryDate || "N/A"}
          </p>
          <div className="flex items-center space-x-1 mt-1">
            <div
              className={`w-2 h-2 rounded-full ${
                licenseInfo.isActivated ? "bg-green-500" : "bg-red-500"
              }`}
            ></div>
            <span className="text-xs text-gray-600">
              {licenseInfo.isActivated ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  const Dashboard = () => {
    const totalStudents = students.length;
    const averagePerformance =
      totalStudents > 0
        ? Math.round(
            students.reduce((sum, student) => {
              const scores = Object.values(student.subjects).map((s) =>
                typeof s === "object" ? (s.term1 + s.term2 + s.term3) / 3 : s
              );
              return sum + scores.reduce((a, b) => a + b, 0) / scores.length;
            }, 0) / totalStudents
          )
        : 0;

    const highPerformers = students.filter((s) => {
      const avg =
        Object.values(s.subjects).reduce((sum, scores) => {
          const score =
            typeof scores === "object"
              ? (scores.term1 + scores.term2 + scores.term3) / 3
              : scores;
          return sum + score;
        }, 0) / Object.keys(s.subjects).length;
      return avg >= 85;
    }).length;

    return (
      <div className="p-6">
        <div className="mb-6">
          <h2
            className="text-2xl font-bold mb-2"
            style={{ color: theme.primary }}
          >
            Welcome to {schoolData.name || "Marka"}
          </h2>
          <p className="text-gray-600">
            Comprehensive school management dashboard
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2
              className="w-8 h-8 animate-spin"
              style={{ color: theme.secondary }}
            />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {[
                {
                  label: "Total Students",
                  value: totalStudents,
                  icon: Users,
                  color: theme.secondary,
                  trend: "+12%",
                },
                {
                  label: "Active Classes",
                  value: getClassList().length - 1,
                  icon: GraduationCap,
                  color: theme.accent,
                  trend: "+2%",
                },
                {
                  label: "Average Performance",
                  value: `${averagePerformance}%`,
                  icon: TrendingUp,
                  color: theme.primary,
                  trend: "+5%",
                },
                {
                  label: "High Performers",
                  value: highPerformers,
                  icon: Award,
                  color: theme.success,
                  trend: "+18%",
                },
              ].map((stat, index) => (
                <div
                  key={index}
                  className="bg-white rounded-lg shadow-sm p-6 border-l-4"
                  style={{ borderColor: stat.color }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-sm text-gray-600">{stat.label}</p>
                      <p
                        className="text-2xl font-bold"
                        style={{ color: theme.primary }}
                      >
                        {stat.value}
                      </p>
                    </div>
                    <stat.icon
                      className="w-8 h-8"
                      style={{ color: stat.color }}
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className="text-xs px-2 py-1 rounded"
                      style={{
                        backgroundColor: `${stat.color}20`,
                        color: stat.color,
                      }}
                    >
                      {stat.trend}
                    </span>
                    <span className="text-xs text-gray-500">vs last term</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
              <div className="lg:col-span-2 bg-white rounded-lg shadow-sm p-6">
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  Recent Activity
                </h3>
                <div className="space-y-4">
                  {[
                    {
                      action: "Report generated",
                      student: "Nakamya Sarah",
                      time: "2 hours ago",
                      type: "success",
                    },
                    {
                      action: "New student added",
                      student: "Musoke David",
                      time: "5 hours ago",
                      type: "info",
                    },
                    {
                      action: "Grades updated",
                      student: "Class P7",
                      time: "1 day ago",
                      type: "warning",
                    },
                    {
                      action: "System backup completed",
                      student: "",
                      time: "2 days ago",
                      type: "success",
                    },
                  ].map((activity, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-4 p-3 rounded-lg bg-gray-50"
                    >
                      <div
                        className={`w-3 h-3 rounded-full ${
                          activity.type === "success"
                            ? "bg-green-500"
                            : activity.type === "warning"
                            ? "bg-yellow-500"
                            : "bg-blue-500"
                        }`}
                      ></div>
                      <div className="flex-1">
                        <p className="font-medium">{activity.action}</p>
                        {activity.student && (
                          <p className="text-sm text-gray-600">
                            {activity.student}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-gray-500">
                        {activity.time}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  Quick Actions
                </h3>
                <div className="space-y-3">
                  {[
                    {
                      label: "Add Student",
                      icon: UserPlus,
                      action: () => openModal("addStudent"),
                    },
                    {
                      label: "Generate Reports",
                      icon: FileText,
                      action: () => setCurrentView("reports"),
                    },
                    {
                      label: "Export Data",
                      icon: Download,
                      action: exportStudentData,
                    },
                    {
                      label: "System Backup",
                      icon: Database,
                      action: handleBackupDatabase,
                    },
                  ].map((action, index) => (
                    <button
                      key={index}
                      onClick={action.action}
                      className="w-full flex items-center space-x-3 p-3 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                    >
                      <action.icon
                        className="w-5 h-5"
                        style={{ color: theme.secondary }}
                      />
                      <span className="text-sm">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  Class Performance Overview
                </h3>
                <div className="space-y-3">
                  {getClassList()
                    .filter((c) => c !== "All")
                    .map((className) => {
                      const classStudents = students.filter(
                        (s) => s.class === className
                      );
                      const avgScore =
                        classStudents.length > 0
                          ? Math.round(
                              classStudents.reduce((sum, student) => {
                                const scores = Object.values(
                                  student.subjects
                                ).map((s) =>
                                  typeof s === "object"
                                    ? (s.term1 + s.term2 + s.term3) / 3
                                    : s
                                );
                                return (
                                  sum +
                                  scores.reduce((a, b) => a + b, 0) /
                                    scores.length
                                );
                              }, 0) / classStudents.length
                            )
                          : 0;

                      return (
                        <div
                          key={className}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded"
                        >
                          <div>
                            <span className="font-medium">
                              Class {className}
                            </span>
                            <span className="text-sm text-gray-600 ml-2">
                              ({classStudents.length} students)
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div
                                className="h-2 rounded-full"
                                style={{
                                  width: `${avgScore}%`,
                                  backgroundColor:
                                    avgScore >= 85
                                      ? theme.success
                                      : avgScore >= 70
                                      ? theme.accent
                                      : theme.error,
                                }}
                              ></div>
                            </div>
                            <span className="text-sm font-medium">
                              {avgScore}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  System Status
                </h3>
                <div className="space-y-4">
                  {[
                    {
                      label: "Database Connection",
                      status: "Connected",
                      icon: Database,
                      color: theme.success,
                    },
                    {
                      label: "License Status",
                      status: licenseInfo.isActivated ? "Active" : "Inactive",
                      icon: Shield,
                      color: licenseInfo.isActivated
                        ? theme.success
                        : theme.error,
                    },
                    {
                      label: "Cloud Sync",
                      status:
                        licenseInfo.type === "Enterprise"
                          ? "Enabled"
                          : "Disabled",
                      icon: Cloud,
                      color:
                        licenseInfo.type === "Enterprise"
                          ? theme.success
                          : theme.warning,
                    },
                    {
                      label: "Local Storage",
                      status: "Healthy",
                      icon: HardDrive,
                      color: theme.success,
                    },
                    {
                      label: "Last Backup",
                      status: "2 days ago",
                      icon: RefreshCw,
                      color: theme.accent,
                    },
                  ].map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center space-x-3">
                        <item.icon
                          className="w-5 h-5"
                          style={{ color: item.color }}
                        />
                        <span className="font-medium">{item.label}</span>
                      </div>
                      <span className="text-sm" style={{ color: item.color }}>
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  const StudentsView = () => (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold" style={{ color: theme.primary }}>
          Students Management
        </h2>
        <div className="flex space-x-3">
          <button
            onClick={() => openModal("importStudents")}
            className="flex items-center space-x-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
            disabled={licenseInfo.type === "Standard"}
          >
            <Upload className="w-4 h-4" />
            <span>Import</span>
          </button>
          <button
            onClick={exportStudentData}
            className="flex items-center space-x-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          <button
            onClick={() => openModal("addStudent")}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: theme.secondary }}
          >
            <Plus className="w-4 h-4" />
            <span>Add Student</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm">
          <div className="p-4 border-b border-gray-200">
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name or student ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                />
              </div>
              <select
                value={filterClass}
                onChange={(e) => setFilterClass(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
              >
                {getClassList().map((className) => (
                  <option key={className} value={className}>
                    {className === "All" ? "All Classes" : `Class ${className}`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Student
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Class
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Performance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Attendance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredStudents.length > 0 ? (
                  filteredStudents.map((student) => {
                    const grade = calculateGrade(
                      student.subjects,
                      student.class.startsWith("P") ? "PLE" : "UCE"
                    );
                    return (
                      <tr key={student.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div
                              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                              style={{ backgroundColor: theme.secondary }}
                            >
                              {student.name
                                .split(" ")
                                .map((n) => n[0])
                                .join("")}
                            </div>
                            <div className="ml-3">
                              <p className="font-medium">{student.name}</p>
                              <p className="text-sm text-gray-500">
                                {student.studentId}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {student.class}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className="inline-flex px-2 py-1 text-xs font-semibold rounded-full text-white"
                            style={{ backgroundColor: grade.color }}
                          >
                            {grade.grade}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <div className="w-16 bg-gray-200 rounded-full h-2">
                              <div
                                className="h-2 rounded-full"
                                style={{
                                  width: `${student.attendance}%`,
                                  backgroundColor:
                                    student.attendance >= 90
                                      ? theme.success
                                      : student.attendance >= 75
                                      ? theme.accent
                                      : theme.error,
                                }}
                              ></div>
                            </div>
                            <span className="text-sm">
                              {student.attendance}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => openModal("editStudent", student)}
                              className="text-blue-600 hover:text-blue-900"
                              title="Edit Student"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => generatePDFReport(student)}
                              className="text-green-600 hover:text-green-900"
                              title="Generate Report"
                            >
                              <FileText className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setSelectedStudent(student)}
                              className="text-purple-600 hover:text-purple-900"
                              title="View Details"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={async () => {
                                const success = await deleteStudent(student.id);
                                if (success) {
                                  const updatedStudents =
                                    await window.electronAPI.students.getAll();
                                  setStudents(updatedStudents);
                                }
                              }}
                              className="text-red-600 hover:text-red-900"
                              title="Delete Student"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td
                      colSpan="5"
                      className="px-6 py-4 text-center text-gray-500"
                    >
                      No students found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const SubjectsView = () => (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold" style={{ color: theme.primary }}>
          Subjects Management
        </h2>
        <button
          onClick={() => openModal("addSubject")}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg text-white transition-colors"
          style={{ backgroundColor: theme.secondary }}
        >
          <BookPlus className="w-4 h-4" />
          <span>Add Subject</span>
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {getClassList()
            .filter((c) => c !== "All")
            .map((className) => (
              <div
                key={className}
                className="bg-white rounded-lg shadow-sm p-6"
              >
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  Class {className} Subjects
                </h3>
                <div className="space-y-3">
                  {subjects
                    .filter((subject) => subject.class === className)
                    .map((subject) => (
                      <div
                        key={subject.id}
                        className="flex items-center justify-between p-3 border rounded-lg"
                      >
                        <div className="flex items-center space-x-3">
                          <BookOpen
                            className="w-5 h-5"
                            style={{ color: theme.secondary }}
                          />
                          <div>
                            <p className="font-medium">{subject.name}</p>
                            <p className="text-sm text-gray-600">
                              {subject.isCore ? "Core Subject" : "Elective"} •
                              Weight: {subject.weight}
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => openModal("editSubject", subject)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={async () => {
                              const success = await deleteSubject(subject.id);
                              if (success) {
                                const updatedSubjects =
                                  await window.electronAPI.subjects.getAll();
                                setSubjects(updatedSubjects);
                              }
                            }}
                            className="text-red-600 hover:text-red-900"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );

  const ReportsView = () => (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold" style={{ color: theme.primary }}>
          Report Generation
        </h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Bulk Report Generation
              </h3>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Class
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent">
                    <option value="">All Classes</option>
                    {getClassList()
                      .filter((c) => c !== "All")
                      .map((className) => (
                        <option key={className} value={className}>
                          Class {className}
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Report Term
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent">
                    <option value="term1">Term 1 2024</option>
                    <option value="term2">Term 2 2024</option>
                    <option value="term3">Term 3 2024</option>
                  </select>
                </div>
              </div>
              <button
                onClick={async () => {
                  try {
                    const result =
                      await window.electronAPI.reports.generateBulk({
                        class: "All",
                        term: "term3",
                      });

                    if (result.success) {
                      showNotification(
                        "Bulk reports generated successfully",
                        "success"
                      );
                    } else {
                      showNotification(
                        `Bulk report generation failed: ${result.error}`,
                        "error"
                      );
                    }
                  } catch (error) {
                    showNotification(
                      "Failed to generate bulk reports",
                      "error"
                    );
                    console.error("Bulk report error:", error);
                  }
                }}
                className="w-full py-3 text-white rounded-lg font-semibold transition-colors"
                style={{ backgroundColor: theme.secondary }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <Printer className="w-5 h-5" />
                  <span>Generate All Reports</span>
                </div>
              </button>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Individual Reports
              </h3>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {students.map((student) => (
                  <div
                    key={student.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-semibold"
                        style={{ backgroundColor: theme.secondary }}
                      >
                        {student.name
                          .split(" ")
                          .map((n) => n[0])
                          .join("")}
                      </div>
                      <div>
                        <p className="font-medium">{student.name}</p>
                        <p className="text-sm text-gray-600">
                          {student.class} • {student.studentId}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => generatePDFReport(student)}
                      className="px-3 py-1 text-sm rounded text-white transition-colors"
                      style={{ backgroundColor: theme.secondary }}
                    >
                      Generate
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Report Templates
              </h3>
              <div className="space-y-3">
                {[
                  {
                    name: "UNEB PLE Standard",
                    description: "Standard Primary Leaving Examination format",
                    preview: true,
                  },
                  {
                    name: "UNEB UCE Standard",
                    description:
                      "Standard Uganda Certificate of Education format",
                    preview: true,
                  },
                  {
                    name: "Custom School Template",
                    description: "Customized template for your school",
                    locked: licenseInfo.type === "Standard",
                    preview: false,
                  },
                  {
                    name: "Detailed Analytics Report",
                    description: "Comprehensive performance analysis",
                    locked: licenseInfo.type !== "Enterprise",
                    preview: false,
                  },
                ].map((template, index) => (
                  <div
                    key={index}
                    className={`p-4 border rounded-lg ${
                      template.locked
                        ? "bg-gray-50"
                        : "hover:shadow-md cursor-pointer"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-medium">{template.name}</h4>
                        <p className="text-sm text-gray-600">
                          {template.description}
                        </p>
                      </div>
                      {template.locked && (
                        <span className="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded">
                          {template.name.includes("Custom")
                            ? "Pro"
                            : "Enterprise"}
                        </span>
                      )}
                    </div>
                    {template.preview && (
                      <button className="text-sm text-blue-600 hover:text-blue-800">
                        Preview Template
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Report Statistics
              </h3>
              <div className="space-y-3">
                {[
                  { label: "Reports This Month", value: "156" },
                  { label: "Total Reports Generated", value: "2,847" },
                  { label: "Average Generation Time", value: "3.2s" },
                  { label: "Success Rate", value: "99.8%" },
                ].map((stat, index) => (
                  <div
                    key={index}
                    className="flex justify-between items-center"
                  >
                    <span className="text-sm text-gray-600">{stat.label}</span>
                    <span
                      className="font-semibold"
                      style={{ color: theme.primary }}
                    >
                      {stat.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const AnalyticsView = () => (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold" style={{ color: theme.primary }}>
          Performance Analytics
        </h2>
        <div className="flex space-x-3">
          <select className="px-3 py-2 border border-gray-300 rounded-lg">
            <option>Current Term</option>
            <option>Previous Term</option>
            <option>Academic Year</option>
          </select>
          <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
            Export Data
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-6">
            {[
              {
                title: "Class Performance Trends",
                chart: "line",
                color: theme.secondary,
              },
              {
                title: "Subject Distribution",
                chart: "pie",
                color: theme.accent,
              },
              {
                title: "Grade Distribution",
                chart: "bar",
                color: theme.primary,
              },
            ].map((chart, index) => (
              <div key={index} className="bg-white rounded-lg shadow-sm p-6">
                <h3
                  className="text-lg font-semibold mb-4"
                  style={{ color: theme.primary }}
                >
                  {chart.title}
                </h3>
                <div className="h-48 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
                  <div className="text-center">
                    <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                    <p className="text-sm text-gray-500">
                      Interactive {chart.chart} chart would appear here
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Data visualization with Chart.js/D3
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Top Performers
              </h3>
              <div className="space-y-3">
                {students
                  .sort((a, b) => {
                    const avgA =
                      Object.values(a.subjects).reduce((sum, scores) => {
                        const score =
                          typeof scores === "object"
                            ? (scores.term1 + scores.term2 + scores.term3) / 3
                            : scores;
                        return sum + score;
                      }, 0) / Object.keys(a.subjects).length;
                    const avgB =
                      Object.values(b.subjects).reduce((sum, scores) => {
                        const score =
                          typeof scores === "object"
                            ? (scores.term1 + scores.term2 + scores.term3) / 3
                            : scores;
                        return sum + score;
                      }, 0) / Object.keys(b.subjects).length;
                    return avgB - avgA;
                  })
                  .slice(0, 5)
                  .map((student, index) => {
                    const avg = Math.round(
                      Object.values(student.subjects).reduce((sum, scores) => {
                        const score =
                          typeof scores === "object"
                            ? (scores.term1 + scores.term2 + scores.term3) / 3
                            : scores;
                        return sum + score;
                      }, 0) / Object.keys(student.subjects).length
                    );

                    return (
                      <div
                        key={student.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded"
                      >
                        <div className="flex items-center space-x-3">
                          <div
                            className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
                            style={{
                              backgroundColor:
                                index === 0
                                  ? "#FFD700"
                                  : index === 1
                                  ? "#C0C0C0"
                                  : index === 2
                                  ? "#CD7F32"
                                  : theme.secondary,
                            }}
                          >
                            {index + 1}
                          </div>
                          <div>
                            <p className="font-medium">{student.name}</p>
                            <p className="text-sm text-gray-600">
                              {student.class}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p
                            className="font-semibold"
                            style={{ color: theme.primary }}
                          >
                            {avg}%
                          </p>
                          <p className="text-sm text-gray-600">Average</p>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Subject Performance Analysis
              </h3>
              <div className="space-y-4">
                {["English", "Mathematics", "Science", "Social Studies"].map(
                  (subject) => {
                    const subjectScores = students
                      .filter((s) => s.subjects[subject])
                      .map((s) => {
                        const scores = s.subjects[subject];
                        return typeof scores === "object"
                          ? (scores.term1 + scores.term2 + scores.term3) / 3
                          : scores;
                      });
                    const avg =
                      subjectScores.length > 0
                        ? Math.round(
                            subjectScores.reduce((a, b) => a + b, 0) /
                              subjectScores.length
                          )
                        : 0;

                    return (
                      <div key={subject}>
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-medium">{subject}</span>
                          <span
                            className="text-sm"
                            style={{ color: theme.primary }}
                          >
                            {avg}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="h-2 rounded-full transition-all duration-300"
                            style={{
                              width: `${avg}%`,
                              backgroundColor:
                                avg >= 85
                                  ? theme.success
                                  : avg >= 70
                                  ? theme.accent
                                  : theme.error,
                            }}
                          ></div>
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );

  const UsersView = () => (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold" style={{ color: theme.primary }}>
          User Management
        </h2>
        <button
          onClick={() => openModal("addUser")}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg text-white transition-colors"
          style={{ backgroundColor: theme.secondary }}
        >
          <UserPlus className="w-4 h-4" />
          <span>Add User</span>
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Login
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                          style={{ backgroundColor: theme.secondary }}
                        >
                          {user.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div className="ml-3">
                          <p className="font-medium">{user.name}</p>
                          <p className="text-sm text-gray-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          user.role === "admin"
                            ? "bg-purple-100 text-purple-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          user.active
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {user.active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      2 hours ago
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button className="text-blue-600 hover:text-blue-900">
                          <Edit className="w-4 h-4" />
                        </button>
                        <button className="text-red-600 hover:text-red-900">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const SettingsView = () => (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6" style={{ color: theme.primary }}>
        Settings
      </h2>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                School Information
              </h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      School Name
                    </label>
                    <input
                      type="text"
                      value={schoolData.name || ""}
                      onChange={(e) =>
                        setSchoolData({ ...schoolData, name: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Principal
                    </label>
                    <input
                      type="text"
                      value={schoolData.principal || ""}
                      onChange={(e) =>
                        setSchoolData({
                          ...schoolData,
                          principal: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Address
                  </label>
                  <textarea
                    value={schoolData.address || ""}
                    onChange={(e) =>
                      setSchoolData({ ...schoolData, address: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    rows="3"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone
                    </label>
                    <input
                      type="text"
                      value={schoolData.phone || ""}
                      onChange={(e) =>
                        setSchoolData({ ...schoolData, phone: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={schoolData.email || ""}
                      onChange={(e) =>
                        setSchoolData({ ...schoolData, email: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Website
                    </label>
                    <input
                      type="url"
                      value={schoolData.website || ""}
                      onChange={(e) =>
                        setSchoolData({
                          ...schoolData,
                          website: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Founded
                    </label>
                    <input
                      type="text"
                      value={schoolData.founded || ""}
                      onChange={(e) =>
                        setSchoolData({
                          ...schoolData,
                          founded: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    School Motto
                  </label>
                  <input
                    type="text"
                    value={schoolData.motto || ""}
                    onChange={(e) =>
                      setSchoolData({ ...schoolData, motto: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                  />
                </div>
                <button
                  onClick={async () => {
                    const success = await saveSettings(
                      "schoolData",
                      schoolData
                    );
                    if (success) {
                      const updatedSettings =
                        await window.electronAPI.settings.getAll();
                      setSettings(updatedSettings);
                    }
                  }}
                  className="w-full py-2 text-white rounded-lg font-semibold transition-colors"
                  style={{ backgroundColor: theme.secondary }}
                >
                  Save School Information
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Grading System Configuration
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Active Grading Schema
                  </label>
                  <select
                    value={activeSchema}
                    onChange={(e) => {
                      setActiveSchema(e.target.value);
                      saveSettings("activeSchema", e.target.value);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
                  >
                    {Object.keys(gradingSchemas).map((schema) => (
                      <option key={schema} value={schema}>
                        {gradingSchemas[schema].name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="p-4 border border-dashed border-gray-300 rounded-lg text-center">
                  <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm text-gray-600">
                    Upload Custom Grading Schema (JSON)
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {licenseInfo.type === "Standard"
                      ? "Pro and Enterprise tiers only"
                      : "Click to upload or drag and drop"}
                  </p>
                  {licenseInfo.type !== "Standard" && (
                    <button
                      onClick={() =>
                        showNotification(
                          "JSON schema upload functionality would be implemented here",
                          "info"
                        )
                      }
                      className="mt-2 px-4 py-2 text-sm rounded text-white"
                      style={{ backgroundColor: theme.secondary }}
                    >
                      Upload Schema
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                System Preferences
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Auto-backup</p>
                    <p className="text-sm text-gray-600">
                      Automatically backup data daily
                    </p>
                  </div>
                  <button
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      settings.autoBackup ? "bg-green-500" : "bg-gray-200"
                    }`}
                    onClick={async () => {
                      const newValue = !settings.autoBackup;
                      await saveSettings("autoBackup", newValue);
                    }}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform ${
                        settings.autoBackup ? "translate-x-6" : "translate-x-1"
                      }`}
                    ></span>
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-gray-600">
                      Send email alerts for important events
                    </p>
                  </div>
                  <button
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      settings.emailNotifications
                        ? "bg-green-500"
                        : "bg-gray-200"
                    }`}
                    onClick={async () => {
                      const newValue = !settings.emailNotifications;
                      await saveSettings("emailNotifications", newValue);
                    }}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform ${
                        settings.emailNotifications
                          ? "translate-x-6"
                          : "translate-x-1"
                      }`}
                    ></span>
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Dark Mode</p>
                    <p className="text-sm text-gray-600">
                      Use dark theme interface
                    </p>
                  </div>
                  <button
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      settings.darkMode ? "bg-blue-500" : "bg-gray-200"
                    }`}
                    onClick={async () => {
                      const newValue = !settings.darkMode;
                      await saveSettings("darkMode", newValue);
                    }}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform ${
                        settings.darkMode ? "translate-x-6" : "translate-x-1"
                      }`}
                    ></span>
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Data Management
              </h3>
              <div className="space-y-3">
                <button
                  onClick={handleBackupDatabase}
                  className="w-full flex items-center justify-center space-x-2 p-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <Database className="w-4 h-4" />
                  <span>Backup Database</span>
                </button>
                <button
                  onClick={exportStudentData}
                  className="w-full flex items-center justify-center space-x-2 p-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Export All Data</span>
                </button>
                <button
                  onClick={() => openModal("importData")}
                  className="w-full flex items-center justify-center space-x-2 p-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                  disabled={licenseInfo.type === "Standard"}
                >
                  <Upload className="w-4 h-4" />
                  <span>Import Data</span>
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Security Settings
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <div>
                    <p className="font-medium">Two-Factor Authentication</p>
                    <p className="text-sm text-gray-600">
                      Enhanced account security
                    </p>
                  </div>
                  <span className="text-sm px-2 py-1 bg-orange-100 text-orange-800 rounded">
                    {licenseInfo.type === "Enterprise"
                      ? "Available"
                      : "Enterprise Only"}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <div>
                    <p className="font-medium">Audit Logging</p>
                    <p className="text-sm text-gray-600">
                      Track all system activities
                    </p>
                  </div>
                  <span className="text-sm px-2 py-1 bg-green-100 text-green-800 rounded">
                    {licenseInfo.type === "Enterprise" ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const LicenseView = () => (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6" style={{ color: theme.primary }}>
        License Management
      </h2>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2
            className="w-8 h-8 animate-spin"
            style={{ color: theme.secondary }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3
                  className="text-lg font-semibold"
                  style={{ color: theme.primary }}
                >
                  Current License
                </h3>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    licenseInfo.isActivated
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {licenseInfo.isActivated ? "Active" : "Inactive"}
                </span>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">License Type</p>
                    <p
                      className="font-semibold text-lg"
                      style={{ color: theme.primary }}
                    >
                      {licenseInfo.type}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Expires</p>
                    <p className="font-semibold">{licenseInfo.expiryDate}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Machine ID</p>
                  <div className="flex items-center space-x-2">
                    <code className="px-2 py-1 bg-gray-100 rounded text-sm font-mono">
                      {licenseInfo.machineId}
                    </code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(licenseInfo.machineId);
                        showNotification(
                          "Machine ID copied to clipboard",
                          "success"
                        );
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Activated On</p>
                  <p className="font-medium">{licenseInfo.activationDate}</p>
                </div>

                <div className="pt-4 border-t">
                  <h4
                    className="font-semibold mb-3"
                    style={{ color: theme.primary }}
                  >
                    Current Plan Features
                  </h4>
                  <div className="space-y-2">
                    {licenseInfo.features?.map((feature, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <CheckCircle
                          className="w-4 h-4"
                          style={{ color: theme.success }}
                        />
                        <span className="text-sm">{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                License Actions
              </h3>
              <div className="space-y-3">
                <button
                  onClick={async () => {
                    try {
                      const result = await window.electronAPI.license.verify();
                      if (result) {
                        showNotification(
                          "License validation successful",
                          "success"
                        );
                        const updatedLicense =
                          await window.electronAPI.license.getInfo();
                        setLicenseInfo(updatedLicense);
                      } else {
                        showNotification("License validation failed", "error");
                      }
                    } catch (error) {
                      showNotification("License validation error", "error");
                      console.error("License verification error:", error);
                    }
                  }}
                  className="w-full flex items-center justify-center space-x-2 p-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Validate License</span>
                </button>
                <button
                  onClick={() => openModal("upgradeLicense")}
                  className="w-full flex items-center justify-center space-x-2 p-3 rounded-lg text-white transition-colors"
                  style={{ backgroundColor: theme.secondary }}
                >
                  <TrendingUp className="w-4 h-4" />
                  <span>Upgrade License</span>
                </button>
                <button
                  onClick={() => openModal("renewLicense")}
                  className="w-full flex items-center justify-center space-x-2 p-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <Calendar className="w-4 h-4" />
                  <span>Renew License</span>
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Available Plans
              </h3>
              <div className="space-y-4">
                {[
                  {
                    name: "Standard",
                    price: "UGX 85,000/month",
                    features: [
                      "UNEB grading for PLE and UCE",
                      "Custom school branding",
                      "Student and subject management",
                      "PDF report card generation",
                      "Up to 2 custom grading profiles",
                    ],
                    limits: {
                      students: 1000,
                      customProfiles: 2,
                      multiUser: false,
                      cloudSync: false,
                      analytics: false,
                    },
                  },
                  {
                    name: "Pro",
                    price: "UGX 125,000/month",
                    features: [
                      "All Standard features",
                      "Unlimited custom grading profiles",
                      "Import/export student data",
                      "Custom report layout editor",
                      "Basic performance analytics",
                    ],
                    limits: {
                      students: 5000,
                      customProfiles: -1,
                      multiUser: false,
                      cloudSync: false,
                      analytics: true,
                    },
                  },
                  {
                    name: "Enterprise",
                    price: "UGX 175,000/month",
                    features: [
                      "All Pro features",
                      "Cloud sync capabilities",
                      "Full analytics dashboard",
                      "Multi-user support with RBAC",
                      "Audit logs and compliance",
                      "Custom PDF themes",
                    ],
                    limits: {
                      students: -1,
                      customProfiles: -1,
                      multiUser: true,
                      cloudSync: true,
                      analytics: true,
                    },
                  },
                ].map((plan, index) => (
                  <div
                    key={index}
                    className={`border-2 rounded-lg p-4 ${
                      plan.name === licenseInfo.type
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-lg">{plan.name}</h4>
                      <span
                        className="text-sm font-medium"
                        style={{ color: theme.secondary }}
                      >
                        {plan.price}
                      </span>
                    </div>
                    <div className="space-y-1 mb-3">
                      {plan.features.slice(0, 3).map((feature, index) => (
                        <div
                          key={index}
                          className="flex items-center space-x-2"
                        >
                          <CheckCircle
                            className="w-3 h-3"
                            style={{ color: theme.success }}
                          />
                          <span className="text-xs text-gray-600">
                            {feature}
                          </span>
                        </div>
                      ))}
                      {plan.features.length > 3 && (
                        <p className="text-xs text-gray-500">
                          +{plan.features.length - 3} more features
                        </p>
                      )}
                    </div>
                    {plan.name !== licenseInfo.type && (
                      <button
                        onClick={async () => {
                          try {
                            const result =
                              await window.electronAPI.license.activate(
                                plan.name
                              );
                            if (result) {
                              showNotification(
                                `Upgraded to ${plan.name} license`,
                                "success"
                              );
                              const updatedLicense =
                                await window.electronAPI.license.getInfo();
                              setLicenseInfo(updatedLicense);
                            } else {
                              showNotification(
                                `Failed to upgrade to ${plan.name}`,
                                "error"
                              );
                            }
                          } catch (error) {
                            showNotification("License upgrade error", "error");
                            console.error("Upgrade error:", error);
                          }
                        }}
                        className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50"
                        style={{
                          borderColor: theme.secondary,
                          color: theme.secondary,
                        }}
                      >
                        {plan.name === "Standard" ? "Downgrade" : "Upgrade"} to{" "}
                        {plan.name}
                      </button>
                    )}
                    {plan.name === licenseInfo.type && (
                      <div className="w-full px-3 py-2 text-sm text-center bg-blue-100 text-blue-800 rounded">
                        Current Plan
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3
                className="text-lg font-semibold mb-4"
                style={{ color: theme.primary }}
              >
                Usage Statistics
              </h3>
              <div className="space-y-4">
                {[
                  {
                    label: "Students",
                    current: students.length,
                    limit: licenseInfo.limits?.students || 1000,
                    unlimited: licenseInfo.limits?.students === -1,
                  },
                  {
                    label: "Custom Profiles",
                    current: Object.keys(gradingSchemas).length,
                    limit: licenseInfo.limits?.customProfiles || 2,
                    unlimited: licenseInfo.limits?.customProfiles === -1,
                  },
                ].map((usage, index) => (
                  <div key={index}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">{usage.label}</span>
                      <span className="text-sm text-gray-600">
                        {usage.current} / {usage.unlimited ? "∞" : usage.limit}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-300"
                        style={{
                          width: usage.unlimited
                            ? "20%"
                            : `${Math.min(
                                (usage.current / usage.limit) * 100,
                                100
                              )}%`,
                          backgroundColor: usage.unlimited
                            ? theme.success
                            : usage.current / usage.limit < 0.8
                            ? theme.success
                            : usage.current / usage.limit < 0.95
                            ? theme.warning
                            : theme.error,
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // Modal Components
  const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between p-6 border-b">
            <h3
              className="text-lg font-semibold"
              style={{ color: theme.primary }}
            >
              {title}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="p-6">{children}</div>
        </div>
      </div>
    );
  };

  const AddStudentModal = () => {
    const [formData, setFormData] = useState({
      name: "",
      studentId: "",
      class: "P7",
      dateOfBirth: "",
      gender: "Male",
    });

    const handleSubmit = async (e) => {
      e.preventDefault();
      const success = await saveStudent(formData);
      if (success) {
        closeModal();
      }
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Full Name
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter student's full name"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Student ID
          </label>
          <input
            type="text"
            required
            value={formData.studentId}
            onChange={(e) =>
              setFormData({ ...formData, studentId: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter unique student ID"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Class
            </label>
            <select
              value={formData.class}
              onChange={(e) =>
                setFormData({ ...formData, class: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="P7">P7</option>
              <option value="S4">S4</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Gender
            </label>
            <select
              value={formData.gender}
              onChange={(e) =>
                setFormData({ ...formData, gender: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Date of Birth
          </label>
          <input
            type="date"
            required
            value={formData.dateOfBirth}
            onChange={(e) =>
              setFormData({ ...formData, dateOfBirth: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
          />
        </div>
        <div className="flex space-x-3 pt-4">
          <button
            type="button"
            onClick={closeModal}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: theme.secondary }}
          >
            Add Student
          </button>
        </div>
      </form>
    );
  };

  const EditStudentModal = () => {
    const [formData, setFormData] = useState(
      selectedStudent || {
        name: "",
        studentId: "",
        class: "P7",
        dateOfBirth: "",
        gender: "Male",
      }
    );

    const handleSubmit = async (e) => {
      e.preventDefault();
      const success = await saveStudent(formData);
      if (success) {
        closeModal();
      }
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Full Name
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter student's full name"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Student ID
          </label>
          <input
            type="text"
            required
            value={formData.studentId}
            onChange={(e) =>
              setFormData({ ...formData, studentId: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter unique student ID"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Class
            </label>
            <select
              value={formData.class}
              onChange={(e) =>
                setFormData({ ...formData, class: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="P7">P7</option>
              <option value="S4">S4</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Gender
            </label>
            <select
              value={formData.gender}
              onChange={(e) =>
                setFormData({ ...formData, gender: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Date of Birth
          </label>
          <input
            type="date"
            required
            value={formData.dateOfBirth}
            onChange={(e) =>
              setFormData({ ...formData, dateOfBirth: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
          />
        </div>
        <div className="flex space-x-3 pt-4">
          <button
            type="button"
            onClick={closeModal}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: theme.secondary }}
          >
            Update Student
          </button>
        </div>
      </form>
    );
  };

  const AddSubjectModal = () => {
    const [formData, setFormData] = useState({
      name: "",
      class: "P7",
      isCore: true,
      weight: 1.0,
    });

    const handleSubmit = async (e) => {
      e.preventDefault();
      const success = await saveSubject(formData);
      if (success) {
        closeModal();
      }
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Subject Name
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter subject name"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Class
            </label>
            <select
              value={formData.class}
              onChange={(e) =>
                setFormData({ ...formData, class: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="P7">P7</option>
              <option value="S4">S4</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Weight
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="2.0"
              value={formData.weight}
              onChange={(e) =>
                setFormData({ ...formData, weight: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            />
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="isCore"
            checked={formData.isCore}
            onChange={(e) =>
              setFormData({ ...formData, isCore: e.target.checked })
            }
            className="w-4 h-4 rounded"
          />
          <label htmlFor="isCore" className="text-sm font-medium text-gray-700">
            Core Subject
          </label>
        </div>
        <div className="flex space-x-3 pt-4">
          <button
            type="button"
            onClick={closeModal}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: theme.secondary }}
          >
            Add Subject
          </button>
        </div>
      </form>
    );
  };

  const EditSubjectModal = () => {
    const [formData, setFormData] = useState(
      selectedSubject || {
        name: "",
        class: "P7",
        isCore: true,
        weight: 1.0,
      }
    );

    const handleSubmit = async (e) => {
      e.preventDefault();
      const success = await saveSubject(formData);
      if (success) {
        closeModal();
      }
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Subject Name
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            placeholder="Enter subject name"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Class
            </label>
            <select
              value={formData.class}
              onChange={(e) =>
                setFormData({ ...formData, class: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            >
              <option value="P7">P7</option>
              <option value="S4">S4</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Weight
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="2.0"
              value={formData.weight}
              onChange={(e) =>
                setFormData({ ...formData, weight: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent"
            />
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="isCore"
            checked={formData.isCore}
            onChange={(e) =>
              setFormData({ ...formData, isCore: e.target.checked })
            }
            className="w-4 h-4 rounded"
          />
          <label htmlFor="isCore" className="text-sm font-medium text-gray-700">
            Core Subject
          </label>
        </div>
        <div className="flex space-x-3 pt-4">
          <button
            type="button"
            onClick={closeModal}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 rounded-lg text-white transition-colors"
            style={{ backgroundColor: theme.secondary }}
          >
            Update Subject
          </button>
        </div>
      </form>
    );
  };

  const ImportStudentsModal = () => {
    const [file, setFile] = useState(null);
    const [isImporting, setIsImporting] = useState(false);

    const handleFileChange = (e) => {
      setFile(e.target.files[0]);
    };

    const handleImport = async () => {
      if (!file) {
        showNotification("Please select a file first", "error");
        return;
      }

      setIsImporting(true);
      try {
        const result = await window.electronAPI.files.importStudents();
        if (result.success) {
          showNotification(
            `${result.data.length} students imported successfully`,
            "success"
          );
          const updatedStudents = await window.electronAPI.students.getAll();
          setStudents(updatedStudents);
          closeModal();
        } else {
          showNotification(`Import failed: ${result.error}`, "error");
        }
      } catch (error) {
        showNotification("Failed to import students", "error");
        console.error("Import error:", error);
      } finally {
        setIsImporting(false);
      }
    };

    return (
      <div className="space-y-4">
        <div className="p-4 border border-dashed border-gray-300 rounded-lg text-center">
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600">
            Upload CSV or Excel file with student data
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            className="hidden"
            id="fileInput"
          />
          <label
            htmlFor="fileInput"
            className="mt-2 px-4 py-2 text-sm rounded text-white inline-block cursor-pointer"
            style={{ backgroundColor: theme.secondary }}
          >
            Select File
          </label>
          {file && (
            <p className="mt-2 text-sm text-gray-600">Selected: {file.name}</p>
          )}
        </div>
        <div className="flex space-x-3 pt-4">
          <button
            onClick={closeModal}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={!file || isImporting}
            className="flex-1 px-4 py-2 rounded-lg text-white transition-colors flex items-center justify-center"
            style={{ backgroundColor: theme.secondary }}
          >
            {isImporting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Importing...
              </>
            ) : (
              "Import Students"
            )}
          </button>
        </div>
      </div>
    );
  };

  // Main render
  return (
    <div
      className="flex h-screen"
      style={{ backgroundColor: theme.background }}
    >
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm border-b px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Menu className="w-5 h-5 text-gray-600 lg:hidden" />
              <div>
                <h1
                  className="text-lg font-semibold"
                  style={{ color: theme.primary }}
                >
                  {currentView.charAt(0).toUpperCase() + currentView.slice(1)}
                </h1>
                <p className="text-sm text-gray-600">
                  {currentView === "dashboard" &&
                    "Overview of your school management system"}
                  {currentView === "students" &&
                    `${filteredStudents.length} students found`}
                  {currentView === "subjects" &&
                    `${subjects.length} subjects configured`}
                  {currentView === "reports" &&
                    "Generate and manage report cards"}
                  {currentView === "analytics" &&
                    "Performance insights and trends"}
                  {currentView === "users" &&
                    "Manage system users and permissions"}
                  {currentView === "settings" &&
                    "System configuration and preferences"}
                  {currentView === "license" &&
                    "License information and management"}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p
                  className="text-sm font-medium"
                  style={{ color: theme.primary }}
                >
                  {schoolData.name || "Marka"}
                </p>
                <p className="text-xs text-gray-600">
                  {licenseInfo.type || "Loading"} License • {students.length}{" "}
                  Students
                </p>
              </div>
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold"
                style={{ backgroundColor: theme.secondary }}
              >
                <User className="w-4 h-4" />
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          {currentView === "dashboard" && <Dashboard />}
          {currentView === "students" && <StudentsView />}
          {currentView === "subjects" && <SubjectsView />}
          {currentView === "reports" && <ReportsView />}
          {currentView === "analytics" && <AnalyticsView />}
          {currentView === "users" && <UsersView />}
          {currentView === "settings" && <SettingsView />}
          {currentView === "license" && <LicenseView />}
        </main>
      </div>

      {/* Modals */}
      <Modal
        isOpen={showModal && modalType === "addStudent"}
        onClose={closeModal}
        title="Add New Student"
      >
        <AddStudentModal />
      </Modal>

      <Modal
        isOpen={showModal && modalType === "editStudent"}
        onClose={closeModal}
        title="Edit Student"
      >
        <EditStudentModal />
      </Modal>

      <Modal
        isOpen={showModal && modalType === "addSubject"}
        onClose={closeModal}
        title="Add New Subject"
      >
        <AddSubjectModal />
      </Modal>

      <Modal
        isOpen={showModal && modalType === "editSubject"}
        onClose={closeModal}
        title="Edit Subject"
      >
        <EditSubjectModal />
      </Modal>

      <Modal
        isOpen={showModal && modalType === "importStudents"}
        onClose={closeModal}
        title="Import Students"
      >
        <ImportStudentsModal />
      </Modal>

      {/* Notification */}
      {notification && (
        <div className="fixed top-4 right-4 z-50">
          <div
            className={`flex items-center space-x-2 px-4 py-3 rounded-lg shadow-lg text-white max-w-sm ${
              notification.type === "success"
                ? "bg-green-500"
                : notification.type === "error"
                ? "bg-red-500"
                : notification.type === "warning"
                ? "bg-yellow-500"
                : "bg-blue-500"
            }`}
          >
            {notification.type === "success" && (
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
            )}
            {notification.type === "error" && (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            {notification.type === "warning" && (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            {notification.type === "info" && (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span className="text-sm">{notification.message}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarkaApp;
