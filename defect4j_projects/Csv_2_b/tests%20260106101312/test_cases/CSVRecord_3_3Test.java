package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_3Test {

    private Map<String, Integer> mapping;
    private String[] values;
    private CSVRecord record;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
        mapping.put("Name", 0);
        mapping.put("Age", 1);
        values = new String[] { "Alice", "30" };
        record = new CSVRecord(values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    public void testGet_WithValidName() {
        assertEquals("Alice", record.get("Name"));
        assertEquals("30", record.get("Age"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNameNotInMapping() {
        assertNull(record.get("NonExistent"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNullMapping_ThrowsException() {
        CSVRecord recordWithNullMapping = createCSVRecordWithNullMapping();

        IllegalStateException thrown = assertThrows(IllegalStateException.class, () -> {
            recordWithNullMapping.get("Name");
        });
        assertEquals(
                "No header mapping was specified, the record values can't be accessed by name",
                thrown.getMessage());
    }

    private CSVRecord createCSVRecordWithNullMapping() {
        try {
            Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(
                    String[].class, Map.class, String.class, long.class);
            constructor.setAccessible(true);
            return constructor.newInstance(new String[] { "Alice", "30" }, null, null, 1L);
        } catch (InstantiationException | IllegalAccessException | InvocationTargetException
                | NoSuchMethodException e) {
            throw new RuntimeException(e);
        }
    }
}