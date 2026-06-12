package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_4Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_nameMappedAndIndexInRange() throws Exception {
        mapping.put("key1", 0);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key1");
        Assertions.assertTrue(result);
    }

    @Test
    public void testisSet_nameMappedButIndexOutOfRange() throws Exception {
        mapping.put("key1", 2);
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key1");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "keyNotMapped");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_emptyValuesArray() throws Exception {
        mapping.put("key1", 0);
        String[] values = {};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(csvRecord, "key1");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_nullName() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        Assertions.assertThrows(NullPointerException.class, () -> {
            method.invoke(csvRecord, (String) null);
        });
    }
}