package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_12_2Test {

    @Test
    public void testToString_emptyValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, new HashMap<>(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testToString_singleValue() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testToString_multipleValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, new HashMap<>(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testToString_withNullValue() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", null, "value3"}, new HashMap<>(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testGet_singleValue() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        String result = record.get(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_outOfBounds() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(1);
        });
    }

    @Test
    public void testSize() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, new HashMap<>(), null, 1);
        Assertions.assertEquals(2, record.size());
    }

    @Test
    public void testIsConsistent() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, new HashMap<>(), null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}