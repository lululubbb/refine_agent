package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_2Test {

    private String[] values;
    private Map<String, Integer> mapping;
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        values = new String[] { "val1", "val2", "val3" };
        mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    public void testGet_WithValidName_ReturnsValue() {
        assertEquals("val1", csvRecord.get("col1"));
        assertEquals("val2", csvRecord.get("col2"));
        assertEquals("val3", csvRecord.get("col3"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNameNotInMapping_ReturnsNull() {
        assertNull(csvRecord.get("nonexistent"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNullMapping_ThrowsIllegalStateException() throws Exception {
        CSVRecord recordWithNullMapping = createCSVRecordWithMapping(null);

        IllegalStateException thrown = assertThrows(IllegalStateException.class, () -> {
            recordWithNullMapping.get("any");
        });
        assertEquals("No header mapping was specified, the record values can't be accessed by name", thrown.getMessage());
    }

    private CSVRecord createCSVRecordWithMapping(Map<String, Integer> map) throws Exception {
        Class<CSVRecord> clazz = CSVRecord.class;
        Constructor<CSVRecord> constructor = clazz.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, map, null, 1L);
    }
}