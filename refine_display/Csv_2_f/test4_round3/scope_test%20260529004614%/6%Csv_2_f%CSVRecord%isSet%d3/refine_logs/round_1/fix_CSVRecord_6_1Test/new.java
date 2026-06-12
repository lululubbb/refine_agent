package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

class CSVRecord_6_1Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() {
        mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        mapping.put("key3", 2);
        String[] values = {"value1", "value2", "value3"};
        csvRecord = new CSVRecord(values, mapping, "comment", 1L);
    }

    @Test
    void testisSet_keyExistsAndMapped() throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key1");
        Assertions.assertEquals(true, result);
    }

    @Test
    void testisSet_keyExistsButNotMapped() throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key3");
        Assertions.assertEquals(true, result);
    }

    @Test
    void testisSet_keyDoesNotExist() throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key4");
        Assertions.assertEquals(false, result);
    }

    @Test
    void testisSet_keyMappedBeyondValuesLength() throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        mapping.put("key5", 3); // Map key5 to an index outside the values array
        boolean result = (boolean) method.invoke(csvRecord, "key5");
        Assertions.assertEquals(false, result);
    }

    @Test
    void testisSet_emptyMapping() throws Exception {
        String[] values = {"value1"};
        CSVRecord emptyMappingRecord = new CSVRecord(values, new HashMap<>(), "comment", 1L);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(emptyMappingRecord, "key1");
        Assertions.assertEquals(false, result);
    }
}