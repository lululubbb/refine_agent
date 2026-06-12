package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

public class CSVRecord_12_1Test {

    @Test
    public void testToString_emptyArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testToString_singleElementArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, Collections.emptyMap(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testToString_multipleElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, Collections.emptyMap(), null, 2);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testToString_nullElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{null, "value2", null}, Collections.emptyMap(), null, 3);
        String result = invokeToString(record);
        Assertions.assertEquals("[null, value2, null]", result);
    }

    @Test
    public void testGet_validIndex() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, Collections.emptyMap(), null, 4);
        String result = record.get(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_invalidIndex() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, Collections.emptyMap(), null, 5);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(2);
        });
    }

    @Test
    public void testSize() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, Collections.emptyMap(), null, 6);
        int size = record.size();
        Assertions.assertEquals(3, size);
    }

    @Test
    public void testIsConsistent() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, Collections.emptyMap(), null, 7);
        boolean result = record.isConsistent();
        Assertions.assertTrue(result);
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}