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

class CSVRecord_5_5Test {

    private Map<String, Integer> mapping;
    private String[] values;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() {
        values = new String[] {"val1", "val2"};
        comment = "comment";
        recordNumber = 1L;
        mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
    }

    @Test
    @Timeout(8000)
    void testIsMappedWithNonNullMappingKeyPresent() {
        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        assertTrue(record.isMapped("key1"));
        assertTrue(record.isMapped("key2"));
    }

    @Test
    @Timeout(8000)
    void testIsMappedWithNonNullMappingKeyAbsent() {
        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        assertFalse(record.isMapped("absentKey"));
    }

    @Test
    @Timeout(8000)
    void testIsMappedWithNullMapping() throws Exception {
        CSVRecord record = createCSVRecordWithNullMapping();
        assertFalse(record.isMapped("anyKey"));
    }

    private CSVRecord createCSVRecordWithNullMapping() throws Exception {
        Class<CSVRecord> clazz = CSVRecord.class;
        Constructor<CSVRecord> constructor = clazz.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, null, comment, recordNumber);
    }
}